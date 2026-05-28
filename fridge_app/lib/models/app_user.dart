class AppUser {
  const AppUser({
    required this.userId,
    required this.name,
    required this.email,
    this.currentFridgeId,
  });

  final int userId;
  final String name;
  final String email;
  final int? currentFridgeId;

  factory AppUser.fromJson(Map<String, dynamic> json) {
    return AppUser(
      userId: json['user_id'] as int,
      name: json['name'] as String,
      email: json['email'] as String,
      currentFridgeId: json['current_fridge_id'] as int?,
    );
  }
}
