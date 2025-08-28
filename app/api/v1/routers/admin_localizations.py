from typing import List, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.security import require_admin
from app.db.session import get_db
from app import models
from app.services.locale.locale_helper import populate_translation_field
from app.services.locale.translation_service import get_translation_service

router = APIRouter(prefix="/admin/localizations", tags=["admin-localizations"])

# supported languages
SUPPORTED_LANGUAGES = ["en", "ru", "kz"]

# pydantic schemas for localization management
class TranslationUpdate(BaseModel):
    """schema for updating translations of a specific entity."""
    translations: Dict[str, str]  # {"en": "English", "ru": "Russian", "kz": "Kazakh"}

class BulkTranslationUpdate(BaseModel):
    """schema for bulk translation updates."""
    entity_type: str  # "category", "menu_item", "modification_type"
    updates: List[Dict]  # [{"id": 1, "translations": {"en": "...", "ru": "..."}}, ...]

class TranslationExport(BaseModel):
    """schema for translation export."""
    entity_type: str
    entity_id: int
    entity_name: str
    translations: Dict[str, str]

class LocalizationStats(BaseModel):
    """schema for localization statistics."""
    total_categories: int
    categories_with_translations: Dict[str, int]
    total_menu_items: int
    menu_items_with_translations: Dict[str, int]
    total_modification_types: int
    modification_types_with_translations: Dict[str, int]
    supported_languages: List[str]

class TranslationRequest(BaseModel):
    """schema for translation requests."""
    text: str
    target_language: str
    source_language: str = "ru"

class TranslationResponse(BaseModel):
    """schema for translation responses."""
    original_text: str
    translated_text: Optional[str]
    source_language: str
    target_language: str
    success: bool
    error: Optional[str] = None


# category translation endpoints
@router.get("/categories", summary="Get all category translations")
async def get_category_translations(
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin)
) -> List[TranslationExport]:
    """get all category translations for management."""
    categories = db.query(models.Category).all()
    
    return [
        TranslationExport(
            entity_type="category",
            entity_id=cat.id,
            entity_name=cat.name,
            translations=cat.name_translations or {}
        )
        for cat in categories
    ]


@router.put("/categories/{category_id}/translations", summary="Update category translations")
async def update_category_translations(
    category_id: int,
    payload: TranslationUpdate,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin)
) -> Dict[str, str]:
    """update translations for a specific category."""
    category = db.query(models.Category).filter(models.Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    # check language codes
    invalid_langs = [lang for lang in payload.translations.keys() if lang not in SUPPORTED_LANGUAGES]
    if invalid_langs:
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported language codes: {invalid_langs}. Supported: {SUPPORTED_LANGUAGES}"
        )
    
    # update translations
    category.name_translations = payload.translations
    db.commit()
    db.refresh(category)
    
    return {"message": "Category translations updated successfully", "translations": category.name_translations}


# menu item translation endpoints
@router.get("/menu-items", summary="Get all menu item translations")
async def get_menu_item_translations(
    category_id: Optional[int] = Query(None, description="Filter by category ID"),
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin)
) -> List[Dict]:
    """get all menu item translations for management."""
    query = db.query(models.MenuItem)
    if category_id:
        query = query.filter(models.MenuItem.category_id == category_id)
    
    menu_items = query.all()
    
    return [
        {
            "entity_type": "menu_item",
            "entity_id": item.id,
            "entity_name": item.name,
            "category_id": item.category_id,
            "name_translations": item.name_translations or {},
            "description_translations": item.description_translations or {}
        }
        for item in menu_items
    ]


@router.put("/menu-items/{item_id}/translations", summary="Update menu item translations")
async def update_menu_item_translations(
    item_id: int,
    name_translations: Optional[Dict[str, str]] = None,
    description_translations: Optional[Dict[str, str]] = None,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin)
) -> Dict[str, str]:
    """update translations for a specific menu item."""
    menu_item = db.query(models.MenuItem).filter(models.MenuItem.id == item_id).first()
    if not menu_item:
        raise HTTPException(status_code=404, detail="Menu item not found")
    
    # check language codes for name translations
    if name_translations:
        invalid_langs = [lang for lang in name_translations.keys() if lang not in SUPPORTED_LANGUAGES]
        if invalid_langs:
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported language codes in name_translations: {invalid_langs}. Supported: {SUPPORTED_LANGUAGES}"
            )
        menu_item.name_translations = name_translations
    
    # check language codes for description translations
    if description_translations:
        invalid_langs = [lang for lang in description_translations.keys() if lang not in SUPPORTED_LANGUAGES]
        if invalid_langs:
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported language codes in description_translations: {invalid_langs}. Supported: {SUPPORTED_LANGUAGES}"
            )
        menu_item.description_translations = description_translations
    
    db.commit()
    db.refresh(menu_item)
    
    return {
        "message": "Menu item translations updated successfully", 
        "name_translations": menu_item.name_translations,
        "description_translations": menu_item.description_translations
    }


# modification type translation endpoints
@router.get("/modification-types", summary="Get all modification type translations")
async def get_modification_type_translations(
    category: Optional[str] = Query(None, description="Filter by category: sauce or removal"),
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin)
) -> List[TranslationExport]:
    """get all modification type translations for management."""
    query = db.query(models.ModificationType)
    if category:
        query = query.filter(models.ModificationType.category == category)
    
    modification_types = query.all()
    
    return [
        TranslationExport(
            entity_type="modification_type",
            entity_id=mod_type.id,
            entity_name=mod_type.name,
            translations=mod_type.name_translations or {}
        )
        for mod_type in modification_types
    ]


@router.put("/modification-types/{type_id}/translations", summary="Update modification type translations")
async def update_modification_type_translations(
    type_id: int,
    payload: TranslationUpdate,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin)
) -> Dict[str, str]:
    """update translations for a specific modification type."""
    mod_type = db.query(models.ModificationType).filter(models.ModificationType.id == type_id).first()
    if not mod_type:
        raise HTTPException(status_code=404, detail="Modification type not found")
    
    # check language codes
    invalid_langs = [lang for lang in payload.translations.keys() if lang not in SUPPORTED_LANGUAGES]
    if invalid_langs:
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported language codes: {invalid_langs}. Supported: {SUPPORTED_LANGUAGES}"
        )
    
    # update translations
    mod_type.name_translations = payload.translations
    db.commit()
    db.refresh(mod_type)
    
    return {"message": "Modification type translations updated successfully", "translations": mod_type.name_translations}


# translation service endpoint
@router.post("/translate", summary="Translate text using AI service")
async def translate_text(
    payload: TranslationRequest,
    _: models.User = Depends(require_admin)
) -> TranslationResponse:
    """translate text using AI translation service (Gemini)."""
    # validate language codes
    if payload.source_language not in SUPPORTED_LANGUAGES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported source language: {payload.source_language}. Supported: {SUPPORTED_LANGUAGES}"
        )
    
    if payload.target_language not in SUPPORTED_LANGUAGES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported target language: {payload.target_language}. Supported: {SUPPORTED_LANGUAGES}"
        )
    
    # check if text is provided
    if not payload.text or not payload.text.strip():
        raise HTTPException(status_code=400, detail="Text to translate cannot be empty")
    
    # get translation service
    translation_service = get_translation_service()
    
    # check if service is available
    if not translation_service.is_available():
        return TranslationResponse(
            original_text=payload.text,
            translated_text=None,
            source_language=payload.source_language,
            target_language=payload.target_language,
            success=False,
            error="Translation service is not available. Please check GEMINI_API_KEY configuration."
        )
    
    # perform translation
    try:
        translated_text = translation_service.translate_text(
            text=payload.text,
            target_language=payload.target_language,
            source_language=payload.source_language
        )
        
        if translated_text:
            return TranslationResponse(
                original_text=payload.text,
                translated_text=translated_text,
                source_language=payload.source_language,
                target_language=payload.target_language,
                success=True
            )
        else:
            return TranslationResponse(
                original_text=payload.text,
                translated_text=None,
                source_language=payload.source_language,
                target_language=payload.target_language,
                success=False,
                error="Translation failed. The AI service could not translate the text."
            )
    except Exception as e:
        return TranslationResponse(
            original_text=payload.text,
            translated_text=None,
            source_language=payload.source_language,
            target_language=payload.target_language,
            success=False,
            error=f"Translation service error: {str(e)}"
        )


# bulk operations
@router.post("/bulk-update", summary="Bulk update translations")
async def bulk_update_translations(
    payload: BulkTranslationUpdate,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin)
) -> Dict[str, int]:
    """bulk update translations for multiple entities."""
    updated_count = 0
    
    if payload.entity_type == "category":
        for update in payload.updates:
            category = db.query(models.Category).filter(models.Category.id == update["id"]).first()
            if category:
                category.name_translations = update["translations"]
                updated_count += 1
    
    elif payload.entity_type == "menu_item":
        for update in payload.updates:
            menu_item = db.query(models.MenuItem).filter(models.MenuItem.id == update["id"]).first()
            if menu_item:
                if "name_translations" in update:
                    menu_item.name_translations = update["name_translations"]
                if "description_translations" in update:
                    menu_item.description_translations = update["description_translations"]
                updated_count += 1
    
    elif payload.entity_type == "modification_type":
        for update in payload.updates:
            mod_type = db.query(models.ModificationType).filter(models.ModificationType.id == update["id"]).first()
            if mod_type:
                mod_type.name_translations = update["translations"]
                updated_count += 1
    
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported entity type: {payload.entity_type}")
    
    db.commit()
    return {"message": f"Bulk update completed", "updated_count": updated_count}


# export/Import operations
@router.get("/export", summary="Export all translations")
async def export_all_translations(
    entity_type: Optional[str] = Query(None, description="Filter by entity type: category, menu_item, modification_type"),
    language: Optional[str] = Query(None, description="Filter by language code"),
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin)
) -> List[TranslationExport]:
    """export all translations for backup or editing."""
    results = []
    
    # export categories
    if not entity_type or entity_type == "category":
        categories = db.query(models.Category).all()
        for cat in categories:
            translations = cat.name_translations or {}
            if language and language in translations:
                translations = {language: translations[language]}
            elif language and language not in translations:
                continue
            
            results.append(TranslationExport(
                entity_type="category",
                entity_id=cat.id,
                entity_name=cat.name,
                translations=translations
            ))
    
    # export menu items
    if not entity_type or entity_type == "menu_item":
        menu_items = db.query(models.MenuItem).all()
        for item in menu_items:
            name_translations = item.name_translations or {}
            desc_translations = item.description_translations or {}
            
            if language:
                name_translations = {language: name_translations.get(language, "")} if language in name_translations else {}
                desc_translations = {language: desc_translations.get(language, "")} if language in desc_translations else {}
                if not name_translations and not desc_translations:
                    continue
            
            results.append({
                "entity_type": "menu_item",
                "entity_id": item.id,
                "entity_name": item.name,
                "name_translations": name_translations,
                "description_translations": desc_translations
            })
    
    # export modification types
    if not entity_type or entity_type == "modification_type":
        mod_types = db.query(models.ModificationType).all()
        for mod_type in mod_types:
            translations = mod_type.name_translations or {}
            if language and language in translations:
                translations = {language: translations[language]}
            elif language and language not in translations:
                continue
                
            results.append(TranslationExport(
                entity_type="modification_type",
                entity_id=mod_type.id,
                entity_name=mod_type.name,
                translations=translations
            ))
    
    return results


# statistics and overview
@router.get("/stats", summary="Get localization statistics")
async def get_localization_stats(
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin)
) -> LocalizationStats:
    """get statistics about translations coverage."""
    
    # category statistics
    categories = db.query(models.Category).all()
    cat_stats = {lang: 0 for lang in SUPPORTED_LANGUAGES}
    for cat in categories:
        if cat.name_translations:
            for lang in SUPPORTED_LANGUAGES:
                if lang in cat.name_translations and cat.name_translations[lang].strip():
                    cat_stats[lang] += 1
    
    # menu item statistics
    menu_items = db.query(models.MenuItem).all()
    item_stats = {lang: 0 for lang in SUPPORTED_LANGUAGES}
    for item in menu_items:
        if item.name_translations:
            for lang in SUPPORTED_LANGUAGES:
                if lang in item.name_translations and item.name_translations[lang].strip():
                    item_stats[lang] += 1
    
    # modification type statistics
    mod_types = db.query(models.ModificationType).all()
    mod_stats = {lang: 0 for lang in SUPPORTED_LANGUAGES}
    for mod_type in mod_types:
        if mod_type.name_translations:
            for lang in SUPPORTED_LANGUAGES:
                if lang in mod_type.name_translations and mod_type.name_translations[lang].strip():
                    mod_stats[lang] += 1
    
    return LocalizationStats(
        total_categories=len(categories),
        categories_with_translations=cat_stats,
        total_menu_items=len(menu_items),
        menu_items_with_translations=item_stats,
        total_modification_types=len(mod_types),
        modification_types_with_translations=mod_stats,
        supported_languages=SUPPORTED_LANGUAGES
    )


# utility endpoints
@router.post("/populate-defaults", summary="Populate default English translations")
async def populate_default_translations(
    entity_type: str = Query(..., description="Entity type: category, menu_item, modification_type"),
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin)
) -> Dict[str, int]:
    """populate default English translations from existing text fields."""
    updated_count = 0
    
    if entity_type == "category":
        categories = db.query(models.Category).all()
        for cat in categories:
            if cat.name and (not cat.name_translations or "en" not in cat.name_translations):
                cat.name_translations = populate_translation_field(cat.name, cat.name_translations)
                updated_count += 1
    
    elif entity_type == "menu_item":
        menu_items = db.query(models.MenuItem).all()
        for item in menu_items:
            updated = False
            if item.name and (not item.name_translations or "en" not in item.name_translations):
                item.name_translations = populate_translation_field(item.name, item.name_translations)
                updated = True
            if item.description and (not item.description_translations or "en" not in item.description_translations):
                item.description_translations = populate_translation_field(item.description, item.description_translations)
                updated = True
            if updated:
                updated_count += 1
    
    elif entity_type == "modification_type":
        mod_types = db.query(models.ModificationType).all()
        for mod_type in mod_types:
            if mod_type.name and (not mod_type.name_translations or "en" not in mod_type.name_translations):
                mod_type.name_translations = populate_translation_field(mod_type.name, mod_type.name_translations)
                updated_count += 1
    
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported entity type: {entity_type}")
    
    db.commit()
    return {"message": f"Populated default translations for {entity_type}", "updated_count": updated_count}