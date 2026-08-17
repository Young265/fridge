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
  bool _isAddingToShoppingList = false;

  @override
  void initState() {
    super.initState();
    _future = ApiService.fetchRecipeDetail(
      fridgeId: widget.fridgeId,
      recipeId: widget.recipeId,
    );
  }

  Future<void> _addMissingIngredients() async {
    setState(() => _isAddingToShoppingList = true);
    try {
      final items = await ApiService.addMissingIngredients(
        fridgeId: widget.fridgeId,
        recipeId: widget.recipeId,
      );
      if (!mounted) {
        return;
      }
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('부족 재료를 장보기 목록에 반영했습니다. 남은 항목 ${items.length}개'),
        ),
      );
    } catch (error) {
      if (!mounted) {
        return;
      }
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(error.toString().replaceFirst('Exception: ', '')),
        ),
      );
    } finally {
      if (mounted) {
        setState(() => _isAddingToShoppingList = false);
      }
    }
  }

  List<String> _splitInstructions(String instructions) {
    final normalized = instructions
        .replaceAll('\r\n', '\n')
        .replaceAll('\r', '\n')
        .trim();
    if (normalized.isEmpty) {
      return const [];
    }

    final numberedSteps = normalized
        .split(RegExp(r'\n(?=\s*\d+[.)]\s*)'))
        .map(
          (step) => step
              .replaceFirst(RegExp(r'^\s*\d+[.)]\s*'), '')
              .replaceAll(RegExp(r'\s*\n\s*'), ' ')
              .trim(),
        )
        .where((step) => step.isNotEmpty)
        .toList();

    if (numberedSteps.length > 1 ||
        RegExp(r'^\s*\d+[.)]\s*').hasMatch(normalized)) {
      return numberedSteps;
    }

    final lineSteps = normalized
        .split('\n')
        .map((step) => step.trim())
        .where((step) => step.isNotEmpty)
        .toList();
    return lineSteps.isEmpty ? [normalized] : lineSteps;
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
          final cookingSteps = recipe.steps.isNotEmpty
              ? recipe.steps
              : _splitInstructions(recipe.instructions).indexed
                    .map(
                      (entry) => RecipeStep(
                        number: entry.$1 + 1,
                        description: entry.$2,
                      ),
                    )
                    .toList();
          return ListView(
            padding: const EdgeInsets.all(20),
            children: [
              if (recipe.imageUrl?.isNotEmpty == true) ...[
                ClipRRect(
                  borderRadius: BorderRadius.circular(20),
                  child: Image.network(
                    recipe.imageUrl!,
                    height: 220,
                    fit: BoxFit.cover,
                    errorBuilder: (_, _, _) => const SizedBox.shrink(),
                  ),
                ),
                const SizedBox(height: 20),
              ],
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
                  if (recipe.calories?.isNotEmpty == true)
                    _DetailChip(label: '열량 ${recipe.calories}'),
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
              if (recipe.missingIngredients.isNotEmpty) ...[
                const SizedBox(height: 12),
                FilledButton.icon(
                  onPressed: _isAddingToShoppingList
                      ? null
                      : _addMissingIngredients,
                  icon: _isAddingToShoppingList
                      ? const SizedBox(
                          width: 18,
                          height: 18,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Icon(Icons.add_shopping_cart_rounded),
                  label: const Text('부족 재료 장보기에 추가'),
                ),
              ],
              const SizedBox(height: 24),
              Row(
                children: [
                  Expanded(
                    child: Text(
                      '조리 순서',
                      style: Theme.of(context).textTheme.titleLarge,
                    ),
                  ),
                  Text(
                    '총 ${cookingSteps.length}단계',
                    style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      color: const Color(0xFF687169),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              if (cookingSteps.isEmpty)
                const _EmptyInstructions()
              else
                ...cookingSteps.indexed.map(
                  (entry) => _CookingStepCard(
                    number: entry.$2.number,
                    description: entry.$2.description,
                    imageUrl: entry.$2.imageUrl,
                    isLast: entry.$1 == cookingSteps.length - 1,
                  ),
                ),
              if (recipe.sourceName?.isNotEmpty == true) ...[
                const SizedBox(height: 28),
                const Divider(),
                const SizedBox(height: 10),
                Text(
                  '자료 출처: ${recipe.sourceName}',
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: const Color(0xFF6B756D),
                  ),
                ),
              ],
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

class _CookingStepCard extends StatelessWidget {
  const _CookingStepCard({
    required this.number,
    required this.description,
    this.imageUrl,
    required this.isLast,
  });

  final int number;
  final String description;
  final String? imageUrl;
  final bool isLast;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.only(bottom: isLast ? 0 : 12),
      child: DecoratedBox(
        decoration: BoxDecoration(
          color: const Color(0xFFF7FAF7),
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: const Color(0xFFE1E8E2)),
        ),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              if (imageUrl?.isNotEmpty == true) ...[
                ClipRRect(
                  borderRadius: BorderRadius.circular(12),
                  child: Image.network(
                    imageUrl!,
                    height: 180,
                    fit: BoxFit.cover,
                    errorBuilder: (_, _, _) => const SizedBox.shrink(),
                  ),
                ),
                const SizedBox(height: 14),
              ],
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Container(
                    width: 32,
                    height: 32,
                    alignment: Alignment.center,
                    decoration: const BoxDecoration(
                      color: Color(0xFF2E7D32),
                      shape: BoxShape.circle,
                    ),
                    child: Text(
                      '$number',
                      style: const TextStyle(
                        color: Colors.white,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ),
                  const SizedBox(width: 14),
                  Expanded(
                    child: Padding(
                      padding: const EdgeInsets.only(top: 4),
                      child: Text(
                        description,
                        style: Theme.of(
                          context,
                        ).textTheme.bodyLarge?.copyWith(height: 1.55),
                      ),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _EmptyInstructions extends StatelessWidget {
  const _EmptyInstructions();

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: const Color(0xFFF4F5F4),
        borderRadius: BorderRadius.circular(16),
      ),
      child: const Row(
        children: [
          Icon(Icons.info_outline_rounded, color: Color(0xFF687169)),
          SizedBox(width: 10),
          Expanded(child: Text('등록된 조리 순서가 없습니다.')),
        ],
      ),
    );
  }
}
