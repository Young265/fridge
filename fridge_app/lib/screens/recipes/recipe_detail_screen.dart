import 'package:flutter/material.dart';

import '../../models/recipe_detail.dart';
import '../../services/api_service.dart';

class RecipeDetailScreen extends StatefulWidget {
  const RecipeDetailScreen({
    super.key,
    required this.fridgeId,
    required this.recipeId,
  });

  final int fridgeId;
  final int recipeId;

  @override
  State<RecipeDetailScreen> createState() => _RecipeDetailScreenState();
}

class _RecipeDetailScreenState extends State<RecipeDetailScreen> {
  late Future<RecipeDetail> _future;

  @override
  void initState() {
    super.initState();
    _future = ApiService.fetchRecipeDetail(
      fridgeId: widget.fridgeId,
      recipeId: widget.recipeId,
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('레시피 상세')),
      body: FutureBuilder<RecipeDetail>(
        future: _future,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snapshot.hasError) {
            return Center(
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: Text(
                  snapshot.error.toString().replaceFirst('Exception: ', ''),
                ),
              ),
            );
          }

          final recipe = snapshot.data!;
          return ListView(
            padding: const EdgeInsets.all(20),
            children: [
              Text(
                recipe.name,
                style: Theme.of(context).textTheme.headlineMedium,
              ),
              const SizedBox(height: 8),
              Text(recipe.description),
              const SizedBox(height: 16),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  _DetailChip(label: '조리 시간 ${recipe.cookingTime}분'),
                  _DetailChip(label: '난이도 ${recipe.difficultyLabel}'),
                  _DetailChip(
                    label: '부족 재료 ${recipe.missingIngredients.length}개',
                  ),
                ],
              ),
              const SizedBox(height: 24),
              Text('필요 재료', style: Theme.of(context).textTheme.titleLarge),
              const SizedBox(height: 12),
              ...recipe.requiredIngredients.map((item) {
                final isMissing = recipe.missingIngredients.any(
                  (missing) => missing.name == item.name,
                );
                return ListTile(
                  contentPadding: EdgeInsets.zero,
                  leading: Icon(
                    isMissing
                        ? Icons.remove_shopping_cart_outlined
                        : Icons.check_circle_outline,
                    color: isMissing
                        ? const Color(0xFFD84315)
                        : const Color(0xFF2E7D32),
                  ),
                  title: Text(item.displayName),
                  trailing: Text('${item.quantityLabel} ${item.unitLabel}'),
                );
              }),
              const SizedBox(height: 24),
              Text('조리 방법', style: Theme.of(context).textTheme.titleLarge),
              const SizedBox(height: 12),
              Text(
                recipe.instructions,
                style: Theme.of(
                  context,
                ).textTheme.bodyLarge?.copyWith(height: 1.6),
              ),
            ],
          );
        },
      ),
    );
  }
}

class _DetailChip extends StatelessWidget {
  const _DetailChip({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: const Color(0xFFFFF3E0),
        borderRadius: BorderRadius.circular(999),
      ),
      child: Text(label),
    );
  }
}
