class Fridge {
  const Fridge({
    required this.fridgeId,
    required this.fridgeName,
    required this.createdAt,
  });

  final int fridgeId;
  final String fridgeName;
  final String createdAt;

  factory Fridge.fromJson(Map<String, dynamic> json) {
    return Fridge(
      fridgeId: json['fridge_id'] as int,
      fridgeName: json['fridge_name'] as String,
      createdAt: json['created_at'] as String,
    );
  }
}
