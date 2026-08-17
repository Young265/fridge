import 'ingredient_labels.dart';

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

  String get displayName => localizedIngredientName(name);
  String get unitLabel => localizedUnit(unit);

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

class RecipeStep {
  const RecipeStep({
    required this.number,
    required this.description,
    this.imageUrl,
  });

  final int number;
  final String description;
  final String? imageUrl;

  factory RecipeStep.fromJson(Map<String, dynamic> json) {
    return RecipeStep(
      number: json['step_number'] as int,
      description: json['description'] as String,
      imageUrl: json['image_url'] as String?,
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
    this.imageUrl,
    this.sourceName,
    this.sourceUrl,
    this.calories,
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
  final String? imageUrl;
  final String? sourceName;
  final String? sourceUrl;
  final String? calories;

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
      imageUrl: json['image_url'] as String?,
      sourceName: json['source_name'] as String?,
      sourceUrl: json['source_url'] as String?,
      calories: json['calories'] as String?,
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
    required this.steps,
    this.imageUrl,
    this.sourceName,
    this.sourceUrl,
    this.calories,
  });

  final int recipeId;
  final String name;
  final String description;
  final String instructions;
  final int cookingTime;
  final String difficulty;
  final List<RecipeIngredient> requiredIngredients;
  final List<RecipeIngredient> missingIngredients;
  final List<RecipeStep> steps;
  final String? imageUrl;
  final String? sourceName;
  final String? sourceUrl;
  final String? calories;

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
      steps: (json['steps'] as List<dynamic>? ?? const [])
          .map((item) => RecipeStep.fromJson(item as Map<String, dynamic>))
          .toList(),
      imageUrl: json['image_url'] as String?,
      sourceName: json['source_name'] as String?,
      sourceUrl: json['source_url'] as String?,
      calories: json['calories'] as String?,
    );
  }
}
