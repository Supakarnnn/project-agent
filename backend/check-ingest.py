def fetch_products_batch(db: Session, limit=1000, offset=0) -> List[Dict[str, Any]]:
    q = text("""
        SELECT
             i  d,
             code,
             name,
             name_eng,
             detail,
             cost,
             brand,
             category_l1,
             category_l2,
             key_features,
             key_ingredients,
             suitable_for_concern,
             size_volume,
             usage_instructions,
             notes
        FROM tbl_material
        ORDER BY id
        LIMIT :limit OFFSET :offset
    """)
    # print(len(q.text))  
    return len(q.text)