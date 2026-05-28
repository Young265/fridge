const Map<String, String> _ingredientLabels = {
  'egg': '계란',
  'milk': '우유',
  'onion': '양파',
  'carrot': '당근',
  'potato': '감자',
  'tomato': '토마토',
  'green_onion': '대파',
  'cheese': '치즈',
  'ham': '햄',
  'tofu': '두부',
  'cabbage': '양배추',
  'mushroom': '버섯',
  'rice': '밥',
  'apple': '사과',
  'banana': '바나나',
  'orange': '오렌지',
  'watermelon': '수박',
  'broccoli': '브로콜리',
  'bottle': '병',
  'cup': '컵',
  'hot_dog': '핫도그',
  'sandwich': '샌드위치',
  'pizza': '피자',
  'donut': '도넛',
  'cake': '케이크',
};

const Map<String, String> _unitLabels = {
  'ea': '개',
  'bowl': '공기',
  'slice': '장',
  'pack': '팩',
  'cup': '컵',
  'head': '통',
};

const Map<String, String> _difficultyLabels = {
  'easy': '쉬움',
  'medium': '보통',
  'hard': '어려움',
  '쉬움': '쉬움',
  '보통': '보통',
  '어려움': '어려움',
};

class RecipeIngredient {
  const RecipeIngredient({
    required this.name,
    required this.quantity,
    required this.unit,
  });

  final String name;
  final double quantity;
  final String unit;

  String get displayName =>
      _ingredientLabels[name] ?? name.replaceAll('_', ' ');
  String get unitLabel => _unitLabels[unit] ?? unit;

  String get quantityLabel {
    if (quantity == quantity.roundToDouble()) {
      return quantity.toInt().toString();
    }
    return quantity.toString();
  }

  factory RecipeIngredient.fromJson(Map<String, dynamic> json) {
    return RecipeIngredient(
      name: json['name'] as String,
      quantity: (json['quantity'] as num).toDouble(),
      unit: json['unit'] as String,
    );
  }
}

class RecipeSummary {
  const RecipeSummary({
    required this.recipeId,
    required this.name,
    required this.description,
    required this.cookingTime,
    required this.difficulty,
    required this.matchedCount,
    required this.requiredCount,
    required this.missingCount,
    required this.missingIngredients,
  });

  final int recipeId;
  final String name;
  final String description;
  final int cookingTime;
  final String difficulty;
  final int matchedCount;
  final int requiredCount;
  final int missingCount;
  final List<RecipeIngredient> missingIngredients;

  String get difficultyLabel => _difficultyLabels[difficulty] ?? difficulty;

  factory RecipeSummary.fromJson(Map<String, dynamic> json) {
    return RecipeSummary(
      recipeId: json['recipe_id'] as int,
      name: json['name'] as String,
      description: json['description'] as String,
      cookingTime: json['cooking_time'] as int,
      difficulty: json['difficulty'] as String,
      matchedCount: json['matched_count'] as int,
      requiredCount: json['required_count'] as int,
      missingCount: json['missing_count'] as int,
      missingIngredients: (json['missing_ingredients'] as List<dynamic>)
          .map(
            (item) => RecipeIngredient.fromJson(item as Map<String, dynamic>),
          )
          .toList(),
    );
  }
}

class RecipeDetail {
  const RecipeDetail({
    required this.recipeId,
    required this.name,
    required this.description,
    required this.instructions,
    required this.cookingTime,
    required this.difficulty,
    required this.requiredIngredients,
    required this.missingIngredients,
  });

  final int recipeId;
  final String name;
  final String description;
  final String instructions;
  final int cookingTime;
  final String difficulty;
  final List<RecipeIngredient> requiredIngredients;
  final List<RecipeIngredient> missingIngredients;

  String get difficultyLabel => _difficultyLabels[difficulty] ?? difficulty;

  factory RecipeDetail.fromJson(Map<String, dynamic> json) {
    return RecipeDetail(
      recipeId: json['recipe_id'] as int,
      name: json['name'] as String,
      description: json['description'] as String,
      instructions: json['instructions'] as String,
      cookingTime: json['cooking_time'] as int,
      difficulty: json['difficulty'] as String,
      requiredIngredients: (json['required_ingredients'] as List<dynamic>)
          .map(
            (item) => RecipeIngredient.fromJson(item as Map<String, dynamic>),
          )
          .toList(),
      missingIngredients: (json['missing_ingredients'] as List<dynamic>)
          .map(
            (item) => RecipeIngredient.fromJson(item as Map<String, dynamic>),
          )
          .toList(),
    );
  }
}
