import 'package:flutter/material.dart';

import '../../models/fridge.dart';
import '../../models/recipe_detail.dart';
import '../../services/api_service.dart';
import 'recipe_detail_screen.dart';

enum _RecipeSort {
  available('보유 재료 우선', 'available'),
  name('이름순', 'name'),
  time('조리시간순', 'time'),
  difficulty('난이도순', 'difficulty');

  const _RecipeSort(this.label, this.apiValue);
  final String label;
  final String apiValue;
}

class RecipeListScreen extends StatefulWidget {
  const RecipeListScreen({super.key, required this.fridge});

  final Fridge fridge;

  @override
  State<RecipeListScreen> createState() => _RecipeListScreenState();
}

class _RecipeListScreenState extends State<RecipeListScreen> {
  final _searchController = TextEditingController();
  late Future<List<RecipeSummary>> _future;
  _RecipeSort _sort = _RecipeSort.available;
  String _difficulty = '';
  bool _availableOnly = false;
  int _limit = 200;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  void _load() {
    _future = ApiService.fetchRecipes(
      fridgeId: widget.fridge.fridgeId,
      query: _searchController.text.trim(),
      sort: _sort.apiValue,
      difficulty: _difficulty,
      availableOnly: _availableOnly,
      limit: _limit,
    );
  }

  Future<void> _applyFilters({bool resetLimit = true}) async {
    if (resetLimit) {
      _limit = 200;
    }
    setState(_load);
    await _future;
  }

  Future<void> _loadMore() async {
    _limit = (_limit + 200).clamp(200, 2000);
    await _applyFilters(resetLimit: false);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('레시피')),
      body: Column(
        children: [
          _FilterPanel(
            controller: _searchController,
            sort: _sort,
            difficulty: _difficulty,
            availableOnly: _availableOnly,
            onSearch: _applyFilters,
            onSortChanged: (value) {
              setState(() => _sort = value);
              _applyFilters();
            },
            onDifficultyChanged: (value) {
              setState(() => _difficulty = value);
              _applyFilters();
            },
            onAvailableOnlyChanged: (value) {
              setState(() => _availableOnly = value);
              _applyFilters();
            },
          ),
          Expanded(
            child: FutureBuilder<List<RecipeSummary>>(
              future: _future,
              builder: (context, snapshot) {
                if (snapshot.connectionState == ConnectionState.waiting) {
                  return const Center(child: CircularProgressIndicator());
                }
                if (snapshot.hasError) {
                  return _LoadError(onRetry: _applyFilters);
                }
                final recipes = snapshot.data ?? const <RecipeSummary>[];
                if (recipes.isEmpty) {
                  return const _EmptyRecipes();
                }
                return RefreshIndicator(
                  onRefresh: _applyFilters,
                  child: ListView.separated(
                    padding: const EdgeInsets.fromLTRB(16, 4, 16, 28),
                    itemCount:
                        recipes.length +
                        (recipes.length == _limit && _limit < 2000 ? 1 : 0),
                    separatorBuilder: (_, _) => const SizedBox(height: 12),
                    itemBuilder: (context, index) {
                      if (index == recipes.length) {
                        return OutlinedButton.icon(
                          onPressed: _loadMore,
                          icon: const Icon(Icons.expand_more_rounded),
                          label: const Text('레시피 더 보기'),
                        );
                      }
                      final recipe = recipes[index];
                      return _RecipeCard(
                        recipe: recipe,
                        onTap: () => Navigator.of(context).push(
                          MaterialPageRoute(
                            builder: (_) => RecipeDetailScreen(
                              fridgeId: widget.fridge.fridgeId,
                              recipeId: recipe.recipeId,
                            ),
                          ),
                        ),
                      );
                    },
                  ),
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}

class _FilterPanel extends StatelessWidget {
  const _FilterPanel({
    required this.controller,
    required this.sort,
    required this.difficulty,
    required this.availableOnly,
    required this.onSearch,
    required this.onSortChanged,
    required this.onDifficultyChanged,
    required this.onAvailableOnlyChanged,
  });

  final TextEditingController controller;
  final _RecipeSort sort;
  final String difficulty;
  final bool availableOnly;
  final Future<void> Function() onSearch;
  final ValueChanged<_RecipeSort> onSortChanged;
  final ValueChanged<String> onDifficultyChanged;
  final ValueChanged<bool> onAvailableOnlyChanged;

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.fromLTRB(16, 4, 16, 16),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: const Color(0xFFE1E8DE)),
      ),
      child: Column(
        children: [
          TextField(
            controller: controller,
            textInputAction: TextInputAction.search,
            onSubmitted: (_) => onSearch(),
            decoration: InputDecoration(
              hintText: '레시피 이름 검색',
              prefixIcon: const Icon(Icons.search_rounded),
              suffixIcon: IconButton(
                tooltip: '검색',
                onPressed: onSearch,
                icon: const Icon(Icons.arrow_forward_rounded),
              ),
              filled: true,
              fillColor: const Color(0xFFF5F7F3),
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(14),
                borderSide: BorderSide.none,
              ),
            ),
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              const Icon(Icons.swap_vert_rounded, size: 20),
              const SizedBox(width: 8),
              Expanded(
                child: DropdownButtonHideUnderline(
                  child: DropdownButton<_RecipeSort>(
                    value: sort,
                    isExpanded: true,
                    items: _RecipeSort.values
                        .map(
                          (option) => DropdownMenuItem(
                            value: option,
                            child: Text(option.label),
                          ),
                        )
                        .toList(),
                    onChanged: (value) {
                      if (value != null) {
                        onSortChanged(value);
                      }
                    },
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Row(
              children: ['', '쉬움', '보통', '어려움'].map((value) {
                return Padding(
                  padding: const EdgeInsets.only(right: 8),
                  child: ChoiceChip(
                    label: Text(value.isEmpty ? '난이도 전체' : value),
                    selected: difficulty == value,
                    onSelected: (_) => onDifficultyChanged(value),
                  ),
                );
              }).toList(),
            ),
          ),
          SwitchListTile(
            contentPadding: EdgeInsets.zero,
            value: availableOnly,
            onChanged: onAvailableOnlyChanged,
            title: const Text('지금 만들 수 있는 레시피만'),
            subtitle: const Text('부족한 재료가 없는 메뉴만 표시'),
          ),
        ],
      ),
    );
  }
}

class _RecipeCard extends StatelessWidget {
  const _RecipeCard({required this.recipe, required this.onTap});

  final RecipeSummary recipe;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final ratio = recipe.requiredCount == 0
        ? 0.0
        : recipe.matchedCount / recipe.requiredCount;
    return Material(
      color: Colors.white,
      borderRadius: BorderRadius.circular(18),
      child: InkWell(
        borderRadius: BorderRadius.circular(18),
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _RecipeImage(imageUrl: recipe.imageUrl),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      recipe.name,
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                    const SizedBox(height: 5),
                    Text(
                      recipe.description,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                    ),
                    const SizedBox(height: 12),
                    Wrap(
                      spacing: 6,
                      runSpacing: 6,
                      children: [
                        _Tag('${recipe.cookingTime}분'),
                        _Tag(recipe.difficultyLabel),
                        if (recipe.calories?.isNotEmpty == true)
                          _Tag(recipe.calories!),
                      ],
                    ),
                    const SizedBox(height: 12),
                    Row(
                      children: [
                        Expanded(
                          child: ClipRRect(
                            borderRadius: BorderRadius.circular(20),
                            child: LinearProgressIndicator(
                              value: ratio.clamp(0.0, 1.0).toDouble(),
                              minHeight: 7,
                              backgroundColor: const Color(0xFFE8ECE6),
                            ),
                          ),
                        ),
                        const SizedBox(width: 10),
                        Text(
                          recipe.missingCount == 0
                              ? '바로 가능'
                              : '부족 ${recipe.missingCount}개',
                          style: TextStyle(
                            color: recipe.missingCount == 0
                                ? const Color(0xFF2F6B4F)
                                : const Color(0xFFC15B2A),
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
              const Icon(Icons.chevron_right_rounded),
            ],
          ),
        ),
      ),
    );
  }
}

class _RecipeImage extends StatelessWidget {
  const _RecipeImage({this.imageUrl});
  final String? imageUrl;

  @override
  Widget build(BuildContext context) {
    final placeholder = Container(
      width: 82,
      height: 104,
      decoration: BoxDecoration(
        color: const Color(0xFFF0F3EC),
        borderRadius: BorderRadius.circular(14),
      ),
      child: const Icon(Icons.restaurant_rounded, color: Color(0xFF60806C)),
    );
    if (imageUrl == null || imageUrl!.isEmpty) {
      return placeholder;
    }
    return ClipRRect(
      borderRadius: BorderRadius.circular(14),
      child: Image.network(
        imageUrl!,
        width: 82,
        height: 104,
        fit: BoxFit.cover,
        errorBuilder: (_, _, _) => placeholder,
      ),
    );
  }
}

class _Tag extends StatelessWidget {
  const _Tag(this.label);
  final String label;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 5),
      decoration: BoxDecoration(
        color: const Color(0xFFF0F3EC),
        borderRadius: BorderRadius.circular(20),
      ),
      child: Text(label, style: Theme.of(context).textTheme.labelMedium),
    );
  }
}

class _LoadError extends StatelessWidget {
  const _LoadError({required this.onRetry});
  final Future<void> Function() onRetry;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: FilledButton.tonalIcon(
        onPressed: onRetry,
        icon: const Icon(Icons.refresh_rounded),
        label: const Text('다시 불러오기'),
      ),
    );
  }
}

class _EmptyRecipes extends StatelessWidget {
  const _EmptyRecipes();

  @override
  Widget build(BuildContext context) {
    return const Center(child: Text('조건에 맞는 레시피가 없습니다.'));
  }
}
