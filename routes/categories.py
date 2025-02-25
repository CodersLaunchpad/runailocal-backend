# Category routes
@app.post("/categories/", response_model=CategoryInDB)
async def create_category(
    category: CategoryCreate,
    current_user: UserInDB = Depends(get_admin_user)
):
    existing_category = await db.categories.find_one({"slug": category.slug})
    if existing_category:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Category with this slug already exists"
        )
    
    category_dict = category.dict()
    result = await db.categories.insert_one(category_dict)
    
    created_category = await db.categories.find_one({"_id": result.inserted_id})
    return created_category

@app.get("/categories/", response_model=List[CategoryInDB])
async def read_categories():
    categories = []
    cursor = db.categories.find({})
    async for document in cursor:
        categories.append(document)
    return categories

@app.get("/categories/{category_id}", response_model=CategoryInDB)
async def read_category(category_id: str):
    try:
        object_id = PyObjectId(category_id)
        category = await db.categories.find_one({"_id": object_id})
        if category:
            return category
        raise HTTPException(status_code=404, detail="Category not found")
    except:
        raise HTTPException(status_code=400, detail="Invalid category ID")

@app.put("/categories/{category_id}", response_model=CategoryInDB)
async def update_category(
    category_id: str,
    category_update: CategoryUpdate,
    current_user: UserInDB = Depends(get_admin_user)
):
    try:
        object_id = PyObjectId(category_id)
        
        # Check if slug is being updated and is unique
        if category_update.slug:
            existing_category = await db.categories.find_one({
                "slug": category_update.slug,
                "_id": {"$ne": object_id}
            })
            if existing_category:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Category with this slug already exists"
                )
        
        update_data = {k: v for k, v in category_update.dict(exclude_unset=True).items() if v is not None}
        
        if update_data:
            updated_category = await db.categories.find_one_and_update(
                {"_id": object_id},
                {"$set": update_data},
                return_document=ReturnDocument.AFTER
            )
            
            if updated_category:
                # If category name or slug changed, update all articles with this category
                if "name" in update_data or "slug" in update_data:
                    await db.articles.update_many(
                        {"category._id": str(object_id)},
                        {"$set": {
                            "category.name": updated_category.get("name"),
                            "category.slug": updated_category.get("slug")
                        }}
                    )
                
                return updated_category
        
        raise HTTPException(status_code=404, detail="Category not found")
    except:
        raise HTTPException(status_code=400, detail="Invalid category ID")

@app.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: str,
    current_user: UserInDB = Depends(get_admin_user)
):
    try:
        object_id = PyObjectId(category_id)
        
        # Check if category has articles
        article_count = await db.articles.count_documents({"category._id": str(object_id)})
        if article_count > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot delete category with {article_count} articles. Reassign articles first."
            )
        
        delete_result = await db.categories.delete_one({"_id": object_id})
        
        if delete_result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Category not found")
        
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except:
        raise HTTPException(status_code=400, detail="Invalid category ID")