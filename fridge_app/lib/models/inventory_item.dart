const Map<String, String> _unitLabels = {
  'ea': '개',
  'bowl': '공기',
  'slice': '장',
  'pack': '팩',
  'cup': '컵',
  'head': '통',
};

class InventoryItem {
  const InventoryItem({
    required this.fridgeItemId,
    required this.fridgeId,
    required this.displayName,
    required this.quantity,
    required this.unit,
    required this.status,
    required this.createdAt,
    required this.updatedAt,
    this.ingredientId,
    this.detectedName,
    this.confidence,
    this.note,
    this.imageUrl,
    this.cropImageUrl,
  });

  final int fridgeItemId;
  final int fridgeId;
  final int? ingredientId;
  final String displayName;
  final double quantity;
  final String unit;
  final String status;
  final String createdAt;
  final String updatedAt;
  final String? detectedName;
  final double? confidence;
  final String? note;
  final String? imageUrl;
  final String? cropImageUrl;

  bool get needsReview => status == 'UNRECOGNIZED';
  String get unitLabel => _unitLabels[unit] ?? unit;

  factory InventoryItem.fromJson(Map<String, dynamic> json) {
    return InventoryItem(
      fridgeItemId: json['fridge_item_id'] as int,
      fridgeId: json['fridge_id'] as int,
      ingredientId: json['ingredient_id'] as int?,
      displayName: json['display_name'] as String,
      quantity: (json['quantity'] as num).toDouble(),
      unit: json['unit'] as String,
      status: json['status'] as String,
      createdAt: json['created_at'] as String,
      updatedAt: json['updated_at'] as String,
      detectedName: json['detected_name'] as String?,
      confidence: (json['confidence'] as num?)?.toDouble(),
      note: json['note'] as String?,
      imageUrl: json['image_url'] as String?,
      cropImageUrl: json['crop_image_url'] as String?,
    );
  }
}
