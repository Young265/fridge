import 'ingredient_labels.dart';

class ShoppingItem {
  const ShoppingItem({
    required this.shoppingItemId,
    required this.fridgeId,
    required this.displayName,
    required this.quantity,
    required this.unit,
    required this.isChecked,
    required this.createdAt,
    required this.updatedAt,
    required this.category,
    required this.estimatedPrice,
    this.ingredientId,
    this.sourceRecipeId,
    this.sourceRecipeName,
    this.note,
  });

  final int shoppingItemId;
  final int fridgeId;
  final int? ingredientId;
  final String displayName;
  final double quantity;
  final String unit;
  final bool isChecked;
  final int? sourceRecipeId;
  final String? sourceRecipeName;
  final String createdAt;
  final String updatedAt;
  final String category;
  final int estimatedPrice;
  final String? note;

  String get nameLabel => localizedIngredientName(displayName);
  String get unitLabel => localizedUnit(unit);
  String get quantityLabel => quantity == quantity.roundToDouble()
      ? quantity.toInt().toString()
      : quantity.toString();

  factory ShoppingItem.fromJson(Map<String, dynamic> json) {
    return ShoppingItem(
      shoppingItemId: json['shopping_item_id'] as int,
      fridgeId: json['fridge_id'] as int,
      ingredientId: json['ingredient_id'] as int?,
      displayName: json['display_name'] as String,
      quantity: (json['quantity'] as num).toDouble(),
      unit: json['unit'] as String,
      isChecked: json['is_checked'] as bool,
      sourceRecipeId: json['source_recipe_id'] as int?,
      sourceRecipeName: json['source_recipe_name'] as String?,
      createdAt: json['created_at'] as String,
      updatedAt: json['updated_at'] as String,
      category: json['category'] as String? ?? '기타',
      estimatedPrice: json['estimated_price'] as int? ?? 0,
      note: json['note'] as String?,
    );
  }
}
