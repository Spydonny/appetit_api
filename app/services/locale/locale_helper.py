"""
Locale helper functions for extracting localized text from database models.
"""
from typing import Dict, Any, Optional


def get_localized_text(translations: Optional[Dict[str, str]], locale: str, fallback_text: Optional[str] = None) -> Optional[str]:
    """
    Extract localized text from translations JSON field.
    
    Args:
        translations: JSON dict with locale keys (e.g., {"en": "English", "ru": "Russian", "kk": "Kazakh"})
        locale: Target locale code (ru, kk, en)
        fallback_text: Fallback text if translations are not available
        
    Returns:
        Localized text or fallback text
    """
    if not translations or not isinstance(translations, dict):
        return fallback_text
    
    # try exact locale match
    if locale in translations:
        return translations[locale]
    
    # try fallback locales in order of preference
    fallback_locales = ["en", "ru", "kk"]
    for fallback_locale in fallback_locales:
        if fallback_locale in translations:
            return translations[fallback_locale]
    
    # if no translations found, return fallback text
    return fallback_text


def get_localized_category_name(category, locale: str) -> str:
    """get localized category name with fallback to original name."""
    return get_localized_text(category.name_translations, locale, category.name) or category.name


def get_localized_menu_item_name(menu_item, locale: str) -> str:
    """get localized menu item name with fallback to original name."""
    return get_localized_text(menu_item.name_translations, locale, menu_item.name) or menu_item.name


def get_localized_menu_item_description(menu_item, locale: str) -> Optional[str]:
    """get localized menu item description with fallback to original description."""
    return get_localized_text(menu_item.description_translations, locale, menu_item.description)


def get_localized_modification_type_name(modification_type, locale: str) -> str:
    """get localized modification type name with fallback to original name."""
    return get_localized_text(modification_type.name_translations, locale, modification_type.name) or modification_type.name


def populate_translation_field(current_text: Optional[str], existing_translations: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    """
    Populate translation field with current text as English default.
    
    Args:
        current_text: Current text value to use as English default
        existing_translations: Existing translations to preserve
        
    Returns:
        Translation dict with English default
    """
    translations = existing_translations.copy() if existing_translations else {}
    
    # set English as default if not already set and current_text is available
    if current_text and "en" not in translations:
        translations["en"] = current_text
    
    return translations