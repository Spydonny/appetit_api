#!/usr/bin/env python3
"""
Data migration script to populate translation fields with existing data as English default.
Run this after adding translation fields to ensure backwards compatibility.
"""
import sys
import os

# add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app import models
from app.services.locale.locale_helper import populate_translation_field


def populate_category_translations():
    """populate category name translations with existing names as English default."""
    print("Populating category translations...")
    db: Session = SessionLocal()
    try:
        categories = db.query(models.Category).all()
        updated_count = 0
        
        for category in categories:
            if category.name and not category.name_translations:
                category.name_translations = populate_translation_field(category.name)
                updated_count += 1
        
        db.commit()
        print(f"Updated {updated_count} categories with translation data")
        
    except Exception as e:
        print(f"Error updating categories: {e}")
        db.rollback()
    finally:
        db.close()


def populate_menu_item_translations():
    """populate menu item name and description translations with existing data as English default."""
    print("Populating menu item translations...")
    db: Session = SessionLocal()
    try:
        menu_items = db.query(models.MenuItem).all()
        updated_count = 0
        
        for item in menu_items:
            needs_update = False
            
            # update name translations
            if item.name and not item.name_translations:
                item.name_translations = populate_translation_field(item.name)
                needs_update = True
            
            # update description translations
            if item.description and not item.description_translations:
                item.description_translations = populate_translation_field(item.description)
                needs_update = True
            
            if needs_update:
                updated_count += 1
        
        db.commit()
        print(f"Updated {updated_count} menu items with translation data")
        
    except Exception as e:
        print(f"Error updating menu items: {e}")
        db.rollback()
    finally:
        db.close()


def populate_modification_type_translations():
    """populate modification type name translations with existing names as English default."""
    print("Populating modification type translations...")
    db: Session = SessionLocal()
    try:
        modification_types = db.query(models.ModificationType).all()
        updated_count = 0
        
        for mod_type in modification_types:
            if mod_type.name and not mod_type.name_translations:
                mod_type.name_translations = populate_translation_field(mod_type.name)
                updated_count += 1
        
        db.commit()
        print(f"Updated {updated_count} modification types with translation data")
        
    except Exception as e:
        print(f"Error updating modification types: {e}")
        db.rollback()
    finally:
        db.close()


def main():
    """run all translation population tasks."""
    print("Starting translation data population...")
    print("=" * 50)
    
    try:
        populate_category_translations()
        print()
        
        populate_menu_item_translations()
        print()
        
        populate_modification_type_translations()
        print()
        
        print("=" * 50)
        print("Translation data population completed successfully!")
        
    except Exception as e:
        print(f"Error during migration: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()