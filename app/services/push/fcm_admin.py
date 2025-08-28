import os
import logging
from typing import Optional, Dict, List, Union
from datetime import datetime, timedelta

try:
    import firebase_admin  # type: ignore
    from firebase_admin import credentials, messaging  # type: ignore
except Exception:  # pragma: no cover
    firebase_admin = None
    credentials = None
    messaging = None

logger = logging.getLogger(__name__)
_initialized = False


def _ensure_init():
    global _initialized
    if _initialized:
        return
    if firebase_admin is None or credentials is None:
        return
    try:
        if not firebase_admin._apps:  # type: ignore
            cred_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
            if not cred_path or not os.path.exists(cred_path):
                return
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
        _initialized = True
    except Exception:
        # leave uninitd for graceful no-op
        _initialized = False


def health_check() -> Dict[str, str]:
    """check FCM integration health and config status."""
    if firebase_admin is None or credentials is None:
        return {"status": "unavailable", "reason": "firebase_library_not_installed"}
    
    cred_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    project_id = os.getenv("FCM_PROJECT_ID")
    
    if not cred_path:
        return {"status": "misconfigured", "reason": "missing_credentials_path"}
    if not os.path.exists(cred_path):
        return {"status": "misconfigured", "reason": "credentials_file_not_found"}
    if not project_id:
        return {"status": "misconfigured", "reason": "missing_project_id"}
    
    _ensure_init()
    if not _initialized:
        return {"status": "error", "reason": "initialization_failed"}
    
    return {"status": "configured", "project_id": project_id, "credentials_file": cred_path}


def send_to_token(
    token: str, 
    title: str, 
    body: str, 
    data: Optional[Dict[str, str]] = None,
    priority: str = "normal",  # normal|high
    ttl: Optional[int] = None  # Time to live in seconds
) -> Dict[str, Union[str, int]]:
    """
    Send a push notification to a specific FCM token.
    
    Args:
        token: FCM registration token
        title: Notification title
        body: Notification body
        data: Optional custom data payload
        priority: Message priority (normal|high)
        ttl: Time to live in seconds
    
    Returns:
        Dict with status, message_id (if successful), or error details
    """
    _ensure_init()
    if messaging is None or not _initialized:
        logger.warning("FCM not configured, skipping token send")
        return {"status": "skipped", "reason": "fcm_not_configured"}
    
    try:
        # build Android config (Android-only)
        android_config = messaging.AndroidConfig(
            priority=priority,
            ttl=timedelta(seconds=ttl) if ttl else None,
        )
        
        msg = messaging.Message(
            token=token,
            notification=messaging.Notification(title=title, body=body),
            data={k: str(v) for k, v in (data or {}).items()},
            android=android_config,
        )
        
        message_id = messaging.send(msg)
        logger.info(f"FCM message sent successfully: {message_id}")
        return {"status": "sent", "id": message_id, "timestamp": datetime.utcnow().isoformat()}
        
    except messaging.UnregisteredError:
        logger.warning(f"FCM token is unregistered: {token[:20]}...")
        return {"status": "error", "reason": "token_unregistered", "error": "Token is no longer valid"}
    except messaging.SenderIdMismatchError:
        logger.error(f"FCM sender ID mismatch for token: {token[:20]}...")
        return {"status": "error", "reason": "sender_id_mismatch", "error": "Invalid sender ID"}
    except messaging.QuotaExceededError:
        logger.error("FCM quota exceeded")
        return {"status": "error", "reason": "quota_exceeded", "error": "FCM quota exceeded"}
    except Exception as e:
        logger.error(f"FCM send failed: {str(e)}")
        return {"status": "error", "reason": "send_failed", "error": str(e)}


def send_batch(
    tokens: List[str],
    title: str,
    body: str,
    data: Optional[Dict[str, str]] = None,
    priority: str = "normal",
    ttl: Optional[int] = None,
    batch_size: int = 500
) -> Dict[str, Union[str, int, List]]:
    """
    Send push notifications to multiple FCM tokens in batches.
    
    Args:
        tokens: List of FCM registration tokens
        title: Notification title
        body: Notification body
        data: Optional custom data payload
        priority: Message priority (normal|high)
        ttl: Time to live in seconds
        batch_size: Maximum batch size (FCM limit is 500)
    
    Returns:
        Dict with overall status, success/failure counts, and detailed results
    """
    _ensure_init()
    if messaging is None or not _initialized:
        logger.warning("FCM not configured, skipping batch send")
        return {"status": "skipped", "reason": "fcm_not_configured", "sent": 0, "failed": len(tokens)}
    
    if not tokens:
        return {"status": "skipped", "reason": "no_tokens"}
    
    # limit batch size to FCM's maximum
    batch_size = min(batch_size, 500)
    total_sent = 0
    total_failed = 0
    message_ids: List[str] = []
    failed_tokens: List[Dict[str, str]] = []
    all_results: List[Dict[str, Union[str, bool]]] = []
    
    try:
        # build Android config (Android-only)
        android_config = messaging.AndroidConfig(
            priority=priority,
            ttl=timedelta(seconds=ttl) if ttl else None,
        )
        
        # process tokens in batches
        for i in range(0, len(tokens), batch_size):
            batch_tokens = tokens[i:i + batch_size]
            
            # create multicast message for this batch
            multicast = messaging.MulticastMessage(
                tokens=batch_tokens,
                notification=messaging.Notification(title=title, body=body),
                data={k: str(v) for k, v in (data or {}).items()},
                android=android_config,
            )
            
            try:
                # send batch
                response = messaging.send_multicast(multicast)
                # compute success/failure counts robustly and cap to batch size
                if hasattr(response, "responses") and response.responses is not None:
                    succ = sum(1 for r in response.responses if getattr(r, "success", False))
                else:
                    succ = min(getattr(response, "success_count", 0), len(batch_tokens))
                fail = len(batch_tokens) - succ
                total_sent += succ
                total_failed += fail
                
                # collect individual results
                for j, res in enumerate(response.responses):
                    if res.success:
                        message_ids.append(getattr(res, "message_id", None) or "")
                    else:
                        err = str(getattr(res, "exception", "unknown error"))
                        if hasattr(messaging, "UnregisteredError") and isinstance(getattr(res, "exception", None), messaging.UnregisteredError):
                            logger.warning(f"Unregistered token in batch: {batch_tokens[j][:20]}...")
                        failed_tokens.append({"token": batch_tokens[j], "error": err})
                
                logger.info(f"Batch {i//batch_size + 1} sent: {response.success_count}/{len(batch_tokens)}")
                
            except Exception as e:
                logger.error(f"Batch {i//batch_size + 1} failed: {str(e)}")
                total_failed += len(batch_tokens)
                for token in batch_tokens:
                    failed_tokens.append({
                        "token": token,
                        "error": str(e)
                    })
        
        logger.info(f"Batch send completed: {total_sent} sent, {total_failed} failed")
        status = "sent" if total_failed == 0 else ("partial" if total_sent > 0 else "failed")
        return {
            "status": status,
            "success_count": total_sent,
            "failure_count": total_failed,
            "message_ids": [mid for mid in message_ids if mid],
            "failed_tokens": failed_tokens,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
    except Exception as e:
        logger.error(f"Batch send failed: {str(e)}")
        return {
            "status": "error",
            "reason": "batch_send_failed",
            "error": str(e),
            "sent": total_sent,
            "failed": len(tokens) - total_sent
        }


def send_to_topic(
    topic: str,
    title: str,
    body: str,
    data: Optional[Dict[str, str]] = None,
    priority: str = "normal",
    ttl: Optional[int] = None
) -> Dict[str, Union[str, int]]:
    """
    Send a push notification to all devices subscribed to a topic.
    
    Args:
        topic: Topic name (without '/topics/' prefix)
        title: Notification title
        body: Notification body
        data: Optional custom data payload
        priority: Message priority (normal|high)
        ttl: Time to live in seconds
    
    Returns:
        Dict with status, message_id (if successful), or error details
    """
    _ensure_init()
    if messaging is None or not _initialized:
        logger.warning("FCM not configured, skipping topic send")
        return {"status": "skipped", "reason": "fcm_not_configured"}
    
    try:
        # build Android config (Android-only)
        android_config = messaging.AndroidConfig(
            priority=priority,
            ttl=timedelta(seconds=ttl) if ttl else None,
        )
        
        msg = messaging.Message(
            topic=topic,
            notification=messaging.Notification(title=title, body=body),
            data={k: str(v) for k, v in (data or {}).items()},
            android=android_config,
        )
        
        message_id = messaging.send(msg)
        logger.info(f"FCM topic message sent successfully to '{topic}': {message_id}")
        return {"status": "sent", "id": message_id, "topic": topic, "timestamp": datetime.utcnow().isoformat()}
        
    except Exception as e:
        logger.error(f"FCM topic send failed for '{topic}': {str(e)}")
        return {"status": "error", "reason": "topic_send_failed", "topic": topic, "error": str(e)}


def subscribe_to_topic(tokens: List[str], topic: str) -> Dict[str, Union[str, int, List]]:
    """
    Subscribe multiple FCM tokens to a topic.
    
    Args:
        tokens: List of FCM registration tokens
        topic: Topic name (without '/topics/' prefix)
    
    Returns:
        Dict with status and subscription results
    """
    _ensure_init()
    if messaging is None or not _initialized:
        logger.warning("FCM not configured, skipping topic subscription")
        return {"status": "skipped", "reason": "fcm_not_configured"}
    
    if not tokens:
        return {"status": "success", "success_count": 0, "failure_count": 0}
    
    try:
        response = messaging.subscribe_to_topic(tokens, topic)
        # determine status
        succ = getattr(response, "success_count", 0)
        fail = getattr(response, "failure_count", 0)
        status = "success" if fail == 0 else ("partial" if succ > 0 else "failed")
        logger.info(f"Topic subscription to '{topic}': {succ}/{len(tokens)} successful")
        
        return {
            "status": status,
            "success_count": succ,
            "failure_count": fail,
            "errors": [str(error.reason) for error in getattr(response, "errors", [])] if getattr(response, "errors", None) else []
        }
        
    except Exception as e:
        logger.error(f"Topic subscription failed for '{topic}': {str(e)}")
        return {"status": "error", "reason": "subscription_failed", "topic": topic, "error": str(e)}


def unsubscribe_from_topic(tokens: List[str], topic: str) -> Dict[str, Union[str, int, List]]:
    """
    Unsubscribe multiple FCM tokens from a topic.
    
    Args:
        tokens: List of FCM registration tokens
        topic: Topic name (without '/topics/' prefix)
    
    Returns:
        Dict with status and unsubscription results
    """
    _ensure_init()
    if messaging is None or not _initialized:
        logger.warning("FCM not configured, skipping topic unsubscription")
        return {"status": "skipped", "reason": "fcm_not_configured"}
    
    if not tokens:
        return {"status": "success", "unsubscribed": 0, "failed": 0}
    
    try:
        response = messaging.unsubscribe_from_topic(tokens, topic)
        logger.info(f"Topic unsubscription from '{topic}': {response.success_count}/{len(tokens)} successful")
        
        return {
            "status": "completed",
            "topic": topic,
            "unsubscribed": response.success_count,
            "failed": response.failure_count,
            "total": len(tokens),
            "timestamp": datetime.utcnow().isoformat(),
            "errors": [str(error.reason) for error in response.errors] if response.errors else []
        }
        
    except Exception as e:
        logger.error(f"Topic unsubscription failed for '{topic}': {str(e)}")
        return {"status": "error", "reason": "unsubscription_failed", "topic": topic, "error": str(e)}
