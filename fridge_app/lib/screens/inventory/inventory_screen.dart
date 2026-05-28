import 'package:flutter/material.dart';

import '../../models/fridge.dart';
import '../../models/inventory_item.dart';
import '../../services/api_service.dart';
import 'inventory_detail_screen.dart';

enum _InventoryFilter {
  all('전체'),
  review('확인 필요'),
  normal('정상');

  const _InventoryFilter(this.label);

  final String label;
}

class InventoryScreen extends StatefulWidget {
  const InventoryScreen({super.key, required this.fridge});

  final Fridge fridge;

  @override
  State<InventoryScreen> createState() => _InventoryScreenState();
}

class _InventoryScreenState extends State<InventoryScreen> {
  late Future<List<InventoryItem>> _future;
  final TextEditingController _searchController = TextEditingController();
  String _query = '';
  _InventoryFilter _filter = _InventoryFilter.all;

  @override
  void initState() {
    super.initState();
    _load();
    _searchController.addListener(() {
      setState(() {
        _query = _searchController.text.trim().toLowerCase();
      });
    });
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  void _load() {
    _future = ApiService.fetchInventory(widget.fridge.fridgeId);
  }

  Future<void> _refresh() async {
    setState(_load);
    await _future;
  }

  Future<void> _openDetail([InventoryItem? item]) async {
    final changed = await Navigator.of(context).push<bool>(
      MaterialPageRoute(
        builder: (_) =>
            InventoryDetailScreen(fridgeId: widget.fridge.fridgeId, item: item),
      ),
    );

    if (changed == true && mounted) {
      await _refresh();
    }
  }

  List<InventoryItem> _visibleItems(List<InventoryItem> items) {
    return items.where((item) {
      final matchesQuery =
          _query.isEmpty ||
          item.displayName.toLowerCase().contains(_query) ||
          (item.detectedName?.toLowerCase().contains(_query) ?? false) ||
          (item.note?.toLowerCase().contains(_query) ?? false);

      final matchesFilter = switch (_filter) {
        _InventoryFilter.all => true,
        _InventoryFilter.review => item.needsReview,
        _InventoryFilter.normal => !item.needsReview,
      };

      return matchesQuery && matchesFilter;
    }).toList();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF6F8F4),
      appBar: AppBar(
        title: Text('${widget.fridge.fridgeName} 재료'),
        backgroundColor: const Color(0xFFF6F8F4),
        surfaceTintColor: Colors.transparent,
        actions: [
          IconButton(
            tooltip: '새로고침',
            onPressed: _refresh,
            icon: const Icon(Icons.refresh_rounded),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => _openDetail(),
        backgroundColor: const Color(0xFF2F6B4F),
        foregroundColor: Colors.white,
        icon: const Icon(Icons.add_rounded),
        label: const Text('재료 추가'),
      ),
      body: FutureBuilder<List<InventoryItem>>(
        future: _future,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const _LoadingState();
          }
          if (snapshot.hasError) {
            return _ErrorState(
              message: snapshot.error.toString().replaceFirst(
                'Exception: ',
                '',
              ),
              onRetry: _refresh,
            );
          }

          final items = snapshot.data ?? [];
          final visibleItems = _visibleItems(items);

          return RefreshIndicator(
            onRefresh: _refresh,
            color: const Color(0xFF2F6B4F),
            child: CustomScrollView(
              physics: const AlwaysScrollableScrollPhysics(),
              slivers: [
                SliverToBoxAdapter(
                  child: _InventoryHeader(
                    fridgeName: widget.fridge.fridgeName,
                    items: items,
                    controller: _searchController,
                    filter: _filter,
                    onFilterChanged: (filter) {
                      setState(() {
                        _filter = filter;
                      });
                    },
                  ),
                ),
                if (items.isEmpty)
                  SliverFillRemaining(
                    hasScrollBody: false,
                    child: _EmptyState(onAdd: () => _openDetail()),
                  )
                else if (visibleItems.isEmpty)
                  SliverFillRemaining(
                    hasScrollBody: false,
                    child: _NoResultState(onClear: _clearSearchAndFilter),
                  )
                else
                  SliverPadding(
                    padding: const EdgeInsets.fromLTRB(20, 4, 20, 104),
                    sliver: SliverGrid.builder(
                      gridDelegate:
                          const SliverGridDelegateWithMaxCrossAxisExtent(
                            maxCrossAxisExtent: 230,
                            mainAxisExtent: 292,
                            crossAxisSpacing: 14,
                            mainAxisSpacing: 14,
                          ),
                      itemCount: visibleItems.length,
                      itemBuilder: (context, index) {
                        final item = visibleItems[index];
                        return _InventoryCard(
                          item: item,
                          onTap: () => _openDetail(item),
                        );
                      },
                    ),
                  ),
              ],
            ),
          );
        },
      ),
    );
  }

  void _clearSearchAndFilter() {
    _searchController.clear();
    setState(() {
      _filter = _InventoryFilter.all;
    });
  }
}

class _InventoryHeader extends StatelessWidget {
  const _InventoryHeader({
    required this.fridgeName,
    required this.items,
    required this.controller,
    required this.filter,
    required this.onFilterChanged,
  });

  final String fridgeName;
  final List<InventoryItem> items;
  final TextEditingController controller;
  final _InventoryFilter filter;
  final ValueChanged<_InventoryFilter> onFilterChanged;

  @override
  Widget build(BuildContext context) {
    final reviewCount = items.where((item) => item.needsReview).length;
    final normalCount = items.length - reviewCount;

    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 8, 20, 20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              color: const Color(0xFFEBF3E8),
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: const Color(0xFFD8E6D3)),
            ),
            child: Row(
              children: [
                Container(
                  width: 54,
                  height: 54,
                  decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(8),
                    boxShadow: [
                      BoxShadow(
                        color: Colors.black.withValues(alpha: 0.06),
                        blurRadius: 16,
                        offset: const Offset(0, 8),
                      ),
                    ],
                  ),
                  child: const Icon(
                    Icons.kitchen_rounded,
                    color: Color(0xFF2F6B4F),
                    size: 30,
                  ),
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        fridgeName,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: Theme.of(context).textTheme.titleLarge?.copyWith(
                          fontWeight: FontWeight.w800,
                          color: const Color(0xFF243528),
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        '총 ${items.length}개 재료 · 확인 필요 $reviewCount개',
                        style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                          color: const Color(0xFF5E6C61),
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),
          Row(
            children: [
              Expanded(
                child: _StatTile(
                  icon: Icons.inventory_2_rounded,
                  label: '전체',
                  value: '${items.length}',
                  color: const Color(0xFF2F6B4F),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: _StatTile(
                  icon: Icons.verified_rounded,
                  label: '정상',
                  value: '$normalCount',
                  color: const Color(0xFF2F6B4F),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: _StatTile(
                  icon: Icons.report_gmailerrorred_rounded,
                  label: '확인',
                  value: '$reviewCount',
                  color: const Color(0xFFC15B2A),
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          TextField(
            controller: controller,
            decoration: InputDecoration(
              hintText: '재료, 메모, 인식 이름 검색',
              prefixIcon: const Icon(Icons.search_rounded),
              suffixIcon: controller.text.isEmpty
                  ? null
                  : IconButton(
                      tooltip: '검색어 지우기',
                      onPressed: controller.clear,
                      icon: const Icon(Icons.close_rounded),
                    ),
              filled: true,
              fillColor: Colors.white,
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(8),
                borderSide: const BorderSide(color: Color(0xFFDDE5DA)),
              ),
              enabledBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(8),
                borderSide: const BorderSide(color: Color(0xFFDDE5DA)),
              ),
              focusedBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(8),
                borderSide: const BorderSide(
                  color: Color(0xFF2F6B4F),
                  width: 1.4,
                ),
              ),
            ),
          ),
          const SizedBox(height: 12),
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Row(
              children: _InventoryFilter.values.map((option) {
                return Padding(
                  padding: const EdgeInsets.only(right: 8),
                  child: ChoiceChip(
                    label: Text(option.label),
                    selected: filter == option,
                    showCheckmark: false,
                    avatar: Icon(switch (option) {
                      _InventoryFilter.all => Icons.grid_view_rounded,
                      _InventoryFilter.review => Icons.error_outline_rounded,
                      _InventoryFilter.normal =>
                        Icons.check_circle_outline_rounded,
                    }, size: 18),
                    selectedColor: const Color(0xFF2F6B4F),
                    labelStyle: TextStyle(
                      color: filter == option
                          ? Colors.white
                          : const Color(0xFF334438),
                      fontWeight: FontWeight.w700,
                    ),
                    side: const BorderSide(color: Color(0xFFDDE5DA)),
                    backgroundColor: Colors.white,
                    onSelected: (_) => onFilterChanged(option),
                  ),
                );
              }).toList(),
            ),
          ),
        ],
      ),
    );
  }
}

class _StatTile extends StatelessWidget {
  const _StatTile({
    required this.icon,
    required this.label,
    required this.value,
    required this.color,
  });

  final IconData icon;
  final String label;
  final String value;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      constraints: const BoxConstraints(minHeight: 84),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: const Color(0xFFE1E8DE)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Icon(icon, color: color, size: 22),
          const SizedBox(height: 8),
          Text(
            value,
            style: Theme.of(context).textTheme.titleLarge?.copyWith(
              fontWeight: FontWeight.w900,
              color: const Color(0xFF26352A),
            ),
          ),
          Text(
            label,
            style: Theme.of(context).textTheme.labelMedium?.copyWith(
              color: const Color(0xFF6E7A70),
              fontWeight: FontWeight.w700,
            ),
          ),
        ],
      ),
    );
  }
}

class _InventoryCard extends StatelessWidget {
  const _InventoryCard({required this.item, required this.onTap});

  final InventoryItem item;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final statusColor = item.needsReview
        ? const Color(0xFFC15B2A)
        : const Color(0xFF2F6B4F);
    final statusBackground = item.needsReview
        ? const Color(0xFFFFF0E8)
        : const Color(0xFFE9F4EA);
    final confidence = item.confidence == null
        ? null
        : '${(item.confidence! * 100).round()}%';
    final metaText = [item.detectedName, confidence].nonNulls.join(' · ');

    return Material(
      color: Colors.white,
      borderRadius: BorderRadius.circular(8),
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: onTap,
        child: Ink(
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(8),
            border: Border.all(color: const Color(0xFFE0E7DD)),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              SizedBox(
                height: 138,
                width: double.infinity,
                child: Stack(
                  fit: StackFit.expand,
                  children: [
                    _InventoryThumbnail(item: item),
                    Positioned(
                      top: 10,
                      left: 10,
                      child: Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 9,
                          vertical: 6,
                        ),
                        decoration: BoxDecoration(
                          color: statusBackground,
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Icon(
                              item.needsReview
                                  ? Icons.priority_high_rounded
                                  : Icons.check_rounded,
                              size: 16,
                              color: statusColor,
                            ),
                            const SizedBox(width: 4),
                            Text(
                              item.needsReview ? '확인 필요' : '정상 등록',
                              style: TextStyle(
                                color: statusColor,
                                fontWeight: FontWeight.w800,
                                fontSize: 12,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ],
                ),
              ),
              Expanded(
                child: Padding(
                  padding: const EdgeInsets.all(14),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        item.displayName,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: Theme.of(context).textTheme.titleMedium
                            ?.copyWith(
                              fontWeight: FontWeight.w900,
                              color: const Color(0xFF233128),
                            ),
                      ),
                      const SizedBox(height: 6),
                      Row(
                        children: [
                          const Icon(
                            Icons.scale_rounded,
                            size: 17,
                            color: Color(0xFF728074),
                          ),
                          const SizedBox(width: 5),
                          Expanded(
                            child: Text(
                              '${_formatQuantity(item.quantity)} ${item.unitLabel}',
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: const TextStyle(
                                color: Color(0xFF56645A),
                                fontWeight: FontWeight.w700,
                              ),
                            ),
                          ),
                        ],
                      ),
                      const Spacer(),
                      if (metaText.isNotEmpty)
                        _CardMetaLine(
                          icon: Icons.auto_awesome_rounded,
                          text: metaText,
                        ),
                      if (item.note != null &&
                          item.note!.trim().isNotEmpty) ...[
                        const SizedBox(height: 6),
                        _CardMetaLine(
                          icon: Icons.sticky_note_2_rounded,
                          text: item.note!,
                        ),
                      ],
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  String _formatQuantity(double quantity) {
    if (quantity == quantity.roundToDouble()) {
      return quantity.toInt().toString();
    }
    return quantity.toStringAsFixed(1);
  }
}

class _CardMetaLine extends StatelessWidget {
  const _CardMetaLine({required this.icon, required this.text});

  final IconData icon;
  final String text;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Icon(icon, size: 15, color: const Color(0xFF8A958B)),
        const SizedBox(width: 5),
        Expanded(
          child: Text(
            text,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: Theme.of(context).textTheme.labelMedium?.copyWith(
              color: const Color(0xFF788379),
              fontWeight: FontWeight.w600,
            ),
          ),
        ),
      ],
    );
  }
}

class _InventoryThumbnail extends StatelessWidget {
  const _InventoryThumbnail({required this.item});

  final InventoryItem item;

  @override
  Widget build(BuildContext context) {
    final imageUrl = item.cropImageUrl ?? item.imageUrl;
    if (imageUrl == null || imageUrl.isEmpty) {
      return _SampleFruitThumbnail(item: item);
    }

    return Image.network(
      imageUrl,
      width: double.infinity,
      fit: BoxFit.cover,
      errorBuilder: (context, error, stackTrace) {
        return _SampleFruitThumbnail(item: item);
      },
    );
  }
}

class _SampleFruitThumbnail extends StatelessWidget {
  const _SampleFruitThumbnail({required this.item});

  static const _assets = [
    'assets/images/sample_fruit_01.jpg',
    'assets/images/sample_fruit_02.jpg',
    'assets/images/sample_fruit_03.jpg',
    'assets/images/sample_fruit_04.jpg',
    'assets/images/sample_fruit_05.jpg',
  ];

  final InventoryItem item;

  @override
  Widget build(BuildContext context) {
    final asset = _assets[item.fridgeItemId.abs() % _assets.length];

    return Image.asset(
      asset,
      width: double.infinity,
      fit: BoxFit.cover,
    );
  }
}

class _ThumbnailFallback extends StatelessWidget {
  const _ThumbnailFallback({required this.icon, required this.label});

  final IconData icon;
  final String label;

  @override
  Widget build(BuildContext context) {
    return Container(
      color: const Color(0xFFE8EFE4),
      child: Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 38, color: const Color(0xFF6F8474)),
            const SizedBox(height: 6),
            Text(
              label,
              style: Theme.of(context).textTheme.labelMedium?.copyWith(
                color: const Color(0xFF6F8474),
                fontWeight: FontWeight.w700,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _LoadingState extends StatelessWidget {
  const _LoadingState();

  @override
  Widget build(BuildContext context) {
    return const Center(
      child: CircularProgressIndicator(color: Color(0xFF2F6B4F)),
    );
  }
}

class _ErrorState extends StatelessWidget {
  const _ErrorState({required this.message, required this.onRetry});

  final String message;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(
              Icons.cloud_off_rounded,
              size: 48,
              color: Color(0xFFC15B2A),
            ),
            const SizedBox(height: 12),
            Text(
              message,
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.bodyLarge,
            ),
            const SizedBox(height: 16),
            FilledButton.icon(
              onPressed: onRetry,
              icon: const Icon(Icons.refresh_rounded),
              label: const Text('다시 시도'),
            ),
          ],
        ),
      ),
    );
  }
}

class _EmptyState extends StatelessWidget {
  const _EmptyState({required this.onAdd});

  final VoidCallback onAdd;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(24, 16, 24, 120),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Icon(
            Icons.add_shopping_cart_rounded,
            size: 52,
            color: Color(0xFF2F6B4F),
          ),
          const SizedBox(height: 12),
          Text(
            '아직 등록된 재료가 없어요',
            style: Theme.of(
              context,
            ).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w800),
          ),
          const SizedBox(height: 8),
          Text(
            '냉장고에 있는 재료를 추가하면 여기에 한눈에 볼 수 있어요.',
            textAlign: TextAlign.center,
            style: Theme.of(
              context,
            ).textTheme.bodyMedium?.copyWith(color: const Color(0xFF66736A)),
          ),
          const SizedBox(height: 18),
          FilledButton.icon(
            onPressed: onAdd,
            icon: const Icon(Icons.add_rounded),
            label: const Text('첫 재료 추가'),
          ),
        ],
      ),
    );
  }
}

class _NoResultState extends StatelessWidget {
  const _NoResultState({required this.onClear});

  final VoidCallback onClear;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(24, 16, 24, 120),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Icon(
            Icons.manage_search_rounded,
            size: 52,
            color: Color(0xFF7A866F),
          ),
          const SizedBox(height: 12),
          Text(
            '조건에 맞는 재료가 없어요',
            style: Theme.of(
              context,
            ).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w800),
          ),
          const SizedBox(height: 8),
          Text(
            '검색어나 필터를 조금 바꿔보면 찾을 수 있을지도 몰라요.',
            textAlign: TextAlign.center,
            style: Theme.of(
              context,
            ).textTheme.bodyMedium?.copyWith(color: const Color(0xFF66736A)),
          ),
          const SizedBox(height: 18),
          OutlinedButton.icon(
            onPressed: onClear,
            icon: const Icon(Icons.filter_alt_off_rounded),
            label: const Text('조건 초기화'),
          ),
        ],
      ),
    );
  }
}
