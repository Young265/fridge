import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;

import '../models/app_user.dart';
import '../models/fridge.dart';
import '../models/inventory_item.dart';
import '../models/recipe_detail.dart';

class AuthResponse {
  const AuthResponse({
    required this.user,
    required this.fridges,
  });

  final AppUser user;
  final List<Fridge> fridges;
}

class ApiService {
  static String get baseUrl {
    if (kIsWeb) {
      return 'http://127.0.0.1:5000';
    }
    return defaultTargetPlatform == TargetPlatform.android
        ? 'http://10.0.2.2:5000'
        : 'http://127.0.0.1:5000';
  }

  static Future<AuthResponse> login({
    required String email,
    required String password,
  }) async {
    final response = await http.post(
      Uri.parse('$baseUrl/auth/login'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'email': email, 'password': password}),
    );
    return _parseAuthResponse(response);
  }

  static Future<AuthResponse> register({
    required String name,
    required String email,
    required String password,
  }) async {
    final response = await http.post(
      Uri.parse('$baseUrl/auth/register'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'name': name, 'email': email, 'password': password}),
    );
    return _parseAuthResponse(response);
  }

  static Future<List<Fridge>> fetchFridges(int userId) async {
    final response = await http.get(Uri.parse('$baseUrl/fridges?user_id=$userId'));
    final data = _decodeList(response);
    return data.map((item) => Fridge.fromJson(item)).toList();
  }

  static Future<Fridge> createFridge({
    required int userId,
    required String fridgeName,
  }) async {
    final response = await http.post(
      Uri.parse('$baseUrl/fridges'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'user_id': userId, 'fridge_name': fridgeName}),
    );
    return Fridge.fromJson(_decodeObject(response));
  }

  static Future<void> deleteFridge(int fridgeId) async {
    final response = await http.delete(Uri.parse('$baseUrl/fridges/$fridgeId'));
    _ensureSuccess(response);
  }

  static Future<void> updateCurrentFridge({
    required int userId,
    required int fridgeId,
  }) async {
    final response = await http.put(
      Uri.parse('$baseUrl/users/$userId/current-fridge'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'fridge_id': fridgeId}),
    );
    _ensureSuccess(response);
  }

  static Future<List<InventoryItem>> fetchInventory(int fridgeId) async {
    final response = await http.get(Uri.parse('$baseUrl/inventory?fridge_id=$fridgeId'));
    final data = _decodeList(response);
    return data.map((item) => InventoryItem.fromJson(_normalizeItemUrls(item))).toList();
  }

  static Future<InventoryItem> createInventoryItem({
    required int fridgeId,
    required String displayName,
    required double quantity,
    required String unit,
    required String status,
    String? note,
  }) async {
    final response = await http.post(
      Uri.parse('$baseUrl/inventory'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({
        'fridge_id': fridgeId,
        'display_name': displayName,
        'quantity': quantity,
        'unit': unit,
        'status': status,
        'note': note,
      }),
    );
    return InventoryItem.fromJson(_normalizeItemUrls(_decodeObject(response)));
  }

  static Future<InventoryItem> updateInventoryItem({
    required int fridgeItemId,
    required String displayName,
    required double quantity,
    required String unit,
    required String status,
    String? note,
  }) async {
    final response = await http.put(
      Uri.parse('$baseUrl/inventory/$fridgeItemId'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({
        'display_name': displayName,
        'quantity': quantity,
        'unit': unit,
        'status': status,
        'note': note,
      }),
    );
    return InventoryItem.fromJson(_normalizeItemUrls(_decodeObject(response)));
  }

  static Future<void> deleteInventoryItem(int fridgeItemId) async {
    final response = await http.delete(Uri.parse('$baseUrl/inventory/$fridgeItemId'));
    _ensureSuccess(response);
  }

  static Future<List<RecipeSummary>> fetchRecipes({
    required int fridgeId,
    String query = '',
  }) async {
    final response = await http.get(
      Uri.parse('$baseUrl/recipes?fridge_id=$fridgeId&q=${Uri.encodeQueryComponent(query)}'),
    );
    final data = _decodeList(response);
    return data.map((item) => RecipeSummary.fromJson(item)).toList();
  }

  static Future<RecipeDetail> fetchRecipeDetail({
    required int fridgeId,
    required int recipeId,
  }) async {
    final response = await http.get(
      Uri.parse('$baseUrl/recipes/$recipeId?fridge_id=$fridgeId'),
    );
    return RecipeDetail.fromJson(_decodeObject(response));
  }

  static AuthResponse _parseAuthResponse(http.Response response) {
    final data = _decodeObject(response);
    return AuthResponse(
      user: AppUser.fromJson(data['user'] as Map<String, dynamic>),
      fridges: (data['fridges'] as List<dynamic>)
          .map((item) => Fridge.fromJson(item as Map<String, dynamic>))
          .toList(),
    );
  }

  static List<Map<String, dynamic>> _decodeList(http.Response response) {
    _ensureSuccess(response);
    final decoded = jsonDecode(response.body) as List<dynamic>;
    return decoded.map((item) => item as Map<String, dynamic>).toList();
  }

  static Map<String, dynamic> _decodeObject(http.Response response) {
    _ensureSuccess(response);
    return jsonDecode(response.body) as Map<String, dynamic>;
  }

  static void _ensureSuccess(http.Response response) {
    if (response.statusCode >= 200 && response.statusCode < 300) {
      return;
    }
    throw Exception(_extractError(response));
  }

  static String _extractError(http.Response response) {
    try {
      final decoded = jsonDecode(response.body) as Map<String, dynamic>;
      return decoded['error'] as String? ?? 'Request failed.';
    } catch (_) {
      return 'Request failed.';
    }
  }

  static Map<String, dynamic> _normalizeItemUrls(Map<String, dynamic> json) {
    final updated = Map<String, dynamic>.from(json);
    for (final key in ['image_url', 'crop_image_url']) {
      final value = updated[key];
      if (value is String && value.startsWith('http://127.0.0.1:5000')) {
        updated[key] = value.replaceFirst('http://127.0.0.1:5000', baseUrl);
      }
    }
    return updated;
  }
}
