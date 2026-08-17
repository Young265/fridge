import 'package:flutter/material.dart';

import '../../models/fridge.dart';
import '../../models/shopping_item.dart';
import '../../services/api_service.dart';

const _categories = ['채소', '과일', '육류', '유제품', '양념', '레시피 재료', '생활용품', '기타'];
const _units = [
  '개',
  '팩',
  '봉지',
  '통',
  '병',
  '묶음',
  '그램',
  '킬로그램',
  '밀리리터',
  '리터',
  '적당량',
];

enum _ShoppingFilter {
  remaining('살 것'),
  all('전체'),
  completed('구매 완료');

  const _ShoppingFilter(this.label);
  final String label;
}

class ShoppingListScreen extends StatefulWidget {
  const ShoppingListScreen({super.key, required this.fridge});
  final Fridge fridge;

  @override
  State<ShoppingListScreen> createState() => _ShoppingListScreenState();
}

class _ShoppingListScreenState extends State<ShoppingListScreen> {
  late Future<List<ShoppingItem>> _future;
  _ShoppingFilter _filter = _ShoppingFilter.remaining;

  @override
  void initState() {
    super.initState();
    _load();
  }

  void _load() {
    _future = ApiService.fetchShoppingList(widget.fridge.fridgeId);
  }

  Future<void> _refresh() async {
    setState(_load);
    await _future;
  }

  Future<void> _toggle(ShoppingItem item, bool checked) async {
    try {
      await ApiService.updateShoppingItem(item: item, isChecked: checked);
      await _refresh();
    } catch (error) {
      _showError(error);
    }
  }

  Future<void> _edit([ShoppingItem? item]) async {
    final draft = await showModalBottomSheet<_ShoppingDraft>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (context) => _ShoppingEditor(item: item),
    );
    if (draft == null) {
      return;
    }

    try {
      if (item == null) {
        await ApiService.createShoppingItem(
          fridgeId: widget.fridge.fridgeId,
          displayName: draft.name,
          quantity: draft.quantity,
          unit: draft.unit,
          category: draft.category,
          estimatedPrice: draft.estimatedPrice,
          note: draft.note,
        );
      } else {
        await ApiService.updateShoppingItem(
          item: item,
          displayName: draft.name,
          quantity: draft.quantity,
          unit: draft.unit,
          category: draft.category,
          estimatedPrice: draft.estimatedPrice,
          note: draft.note,
        );
      }
      await _refresh();
    } catch (error) {
      _showError(error);
    }
  }

  Future<void> _delete(ShoppingItem item) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('항목 삭제'),
        content: Text('${item.nameLabel}을(를) 목록에서 삭제할까요?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('취소'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('삭제'),
          ),
        ],
      ),
    );
    if (confirmed != true) {
      return;
    }
    try {
      await ApiService.deleteShoppingItem(item.shoppingItemId);
      await _refresh();
    } catch (error) {
      _showError(error);
    }
  }

  void _showError(Object error) {
    if (!mounted) {
      return;
    }
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(error.toString().replaceFirst('Exception: ', ''))),
    );
  }

  List<ShoppingItem> _filtered(List<ShoppingItem> items) {
    return switch (_filter) {
      _ShoppingFilter.remaining =>
        items.where((item) => !item.isChecked).toList(),
      _ShoppingFilter.completed =>
        items.where((item) => item.isChecked).toList(),
      _ShoppingFilter.all => items,
    };
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('장보기'),
        actions: [
          IconButton(
            tooltip: '새로고침',
            onPressed: _refresh,
            icon: const Icon(Icons.refresh_rounded),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _edit,
        icon: const Icon(Icons.add_rounded),
        label: const Text('항목 추가'),
      ),
      body: FutureBuilder<List<ShoppingItem>>(
        future: _future,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snapshot.hasError) {
            return Center(
              child: FilledButton.tonalIcon(
                onPressed: _refresh,
                icon: const Icon(Icons.refresh_rounded),
                label: const Text('다시 불러오기'),
              ),
            );
          }

          final items = snapshot.data ?? const <ShoppingItem>[];
          final visible = _filtered(items);
          return RefreshIndicator(
            onRefresh: _refresh,
            child: CustomScrollView(
              physics: const AlwaysScrollableScrollPhysics(),
              slivers: [
                SliverToBoxAdapter(
                  child: _ShoppingSummary(
                    items: items,
                    filter: _filter,
                    onFilterChanged: (value) => setState(() => _filter = value),
                  ),
                ),
                if (visible.isEmpty)
                  SliverFillRemaining(
                    hasScrollBody: false,
                    child: _EmptyShoppingList(filter: _filter),
                  )
                else
                  SliverPadding(
                    padding: const EdgeInsets.fromLTRB(16, 0, 16, 100),
                    sliver: SliverList.separated(
                      itemCount: visible.length,
                      separatorBuilder: (_, _) => const SizedBox(height: 10),
                      itemBuilder: (context, index) {
                        final item = visible[index];
                        return _ShoppingCard(
                          item: item,
                          onToggle: (value) => _toggle(item, value),
                          onEdit: () => _edit(item),
                          onDelete: () => _delete(item),
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
}

class _ShoppingSummary extends StatelessWidget {
  const _ShoppingSummary({
    required this.items,
    required this.filter,
    required this.onFilterChanged,
  });

  final List<ShoppingItem> items;
  final _ShoppingFilter filter;
  final ValueChanged<_ShoppingFilter> onFilterChanged;

  @override
  Widget build(BuildContext context) {
    final completed = items.where((item) => item.isChecked).length;
    final remaining = items.length - completed;
    final totalPrice = items
        .where((item) => !item.isChecked)
        .fold<int>(0, (sum, item) => sum + item.estimatedPrice);
    final progress = items.isEmpty ? 0.0 : completed / items.length;

    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 4, 16, 16),
      child: Column(
        children: [
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              gradient: const LinearGradient(
                colors: [Color(0xFF2F6B4F), Color(0xFF4C8468)],
              ),
              borderRadius: BorderRadius.circular(22),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  '살 것 $remaining개',
                  style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                    color: Colors.white,
                    fontWeight: FontWeight.w900,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  '예상 금액 ${_won(totalPrice)}',
                  style: const TextStyle(color: Colors.white70),
                ),
                const SizedBox(height: 16),
                ClipRRect(
                  borderRadius: BorderRadius.circular(20),
                  child: LinearProgressIndicator(
                    value: progress,
                    minHeight: 9,
                    color: Colors.white,
                    backgroundColor: Colors.white24,
                  ),
                ),
                const SizedBox(height: 8),
                Text(
                  '전체 ${items.length}개 중 $completed개 구매 완료',
                  style: const TextStyle(color: Colors.white70),
                ),
              ],
            ),
          ),
          const SizedBox(height: 14),
          Row(
            children: _ShoppingFilter.values.map((option) {
              return Expanded(
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 3),
                  child: ChoiceChip(
                    label: SizedBox(
                      width: double.infinity,
                      child: Text(option.label, textAlign: TextAlign.center),
                    ),
                    selected: filter == option,
                    onSelected: (_) => onFilterChanged(option),
                  ),
                ),
              );
            }).toList(),
          ),
        ],
      ),
    );
  }
}

class _ShoppingCard extends StatelessWidget {
  const _ShoppingCard({
    required this.item,
    required this.onToggle,
    required this.onEdit,
    required this.onDelete,
  });

  final ShoppingItem item;
  final ValueChanged<bool> onToggle;
  final VoidCallback onEdit;
  final VoidCallback onDelete;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.white,
      borderRadius: BorderRadius.circular(18),
      child: InkWell(
        borderRadius: BorderRadius.circular(18),
        onTap: onEdit,
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
          child: Row(
            children: [
              Checkbox(
                value: item.isChecked,
                onChanged: (value) => onToggle(value ?? false),
              ),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      item.nameLabel,
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.w800,
                        decoration: item.isChecked
                            ? TextDecoration.lineThrough
                            : null,
                        color: item.isChecked ? Colors.grey : null,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      '${item.quantityLabel} ${item.unitLabel} · ${item.category}',
                      style: const TextStyle(color: Color(0xFF68736B)),
                    ),
                    if (item.note?.isNotEmpty == true)
                      Text(
                        item.note!,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: Theme.of(context).textTheme.bodySmall,
                      ),
                    if (item.sourceRecipeName?.isNotEmpty == true)
                      Text(
                        '${item.sourceRecipeName}에서 추가',
                        style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          color: const Color(0xFF2F6B4F),
                        ),
                      ),
                  ],
                ),
              ),
              Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  if (item.estimatedPrice > 0)
                    Text(
                      _won(item.estimatedPrice),
                      style: const TextStyle(fontWeight: FontWeight.w800),
                    ),
                  PopupMenuButton<String>(
                    tooltip: '항목 메뉴',
                    onSelected: (value) {
                      if (value == '수정') {
                        onEdit();
                      }
                      if (value == '삭제') {
                        onDelete();
                      }
                    },
                    itemBuilder: (_) => const [
                      PopupMenuItem(value: '수정', child: Text('수정')),
                      PopupMenuItem(value: '삭제', child: Text('삭제')),
                    ],
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

class _ShoppingEditor extends StatefulWidget {
  const _ShoppingEditor({this.item});
  final ShoppingItem? item;

  @override
  State<_ShoppingEditor> createState() => _ShoppingEditorState();
}

class _ShoppingEditorState extends State<_ShoppingEditor> {
  late final TextEditingController _name;
  late final TextEditingController _quantity;
  late final TextEditingController _price;
  late final TextEditingController _note;
  late String _unit;
  late String _category;

  @override
  void initState() {
    super.initState();
    final item = widget.item;
    _name = TextEditingController(text: item?.nameLabel ?? '');
    _quantity = TextEditingController(text: item?.quantityLabel ?? '1');
    _price = TextEditingController(
      text: item == null || item.estimatedPrice == 0
          ? ''
          : '${item.estimatedPrice}',
    );
    _note = TextEditingController(text: item?.note ?? '');
    _unit = item != null && _units.contains(item.unitLabel)
        ? item.unitLabel
        : '개';
    _category = item != null && _categories.contains(item.category)
        ? item.category
        : '기타';
  }

  @override
  void dispose() {
    _name.dispose();
    _quantity.dispose();
    _price.dispose();
    _note.dispose();
    super.dispose();
  }

  void _submit() {
    final name = _name.text.trim();
    final quantity = double.tryParse(_quantity.text.trim());
    final price = int.tryParse(_price.text.replaceAll(',', '').trim()) ?? 0;
    if (name.isEmpty || quantity == null || quantity <= 0 || price < 0) {
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(const SnackBar(content: Text('이름과 올바른 수량을 입력해 주세요.')));
      return;
    }
    Navigator.pop(
      context,
      _ShoppingDraft(
        name: name,
        quantity: quantity,
        unit: _unit,
        category: _category,
        estimatedPrice: price,
        note: _note.text.trim().isEmpty ? null : _note.text.trim(),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: EdgeInsets.fromLTRB(
        20,
        12,
        20,
        MediaQuery.viewInsetsOf(context).bottom + 24,
      ),
      decoration: const BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.vertical(top: Radius.circular(28)),
      ),
      child: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Center(
              child: Container(
                width: 42,
                height: 4,
                decoration: BoxDecoration(
                  color: const Color(0xFFD3D8D3),
                  borderRadius: BorderRadius.circular(10),
                ),
              ),
            ),
            const SizedBox(height: 18),
            Text(
              widget.item == null ? '장보기 항목 추가' : '장보기 항목 수정',
              style: Theme.of(
                context,
              ).textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.w900),
            ),
            const SizedBox(height: 18),
            TextField(
              controller: _name,
              autofocus: widget.item == null,
              decoration: const InputDecoration(
                labelText: '품목 이름',
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _quantity,
                    keyboardType: const TextInputType.numberWithOptions(
                      decimal: true,
                    ),
                    decoration: const InputDecoration(
                      labelText: '수량',
                      border: OutlineInputBorder(),
                    ),
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: DropdownButtonFormField<String>(
                    initialValue: _unit,
                    decoration: const InputDecoration(
                      labelText: '단위',
                      border: OutlineInputBorder(),
                    ),
                    items: _units
                        .map(
                          (unit) =>
                              DropdownMenuItem(value: unit, child: Text(unit)),
                        )
                        .toList(),
                    onChanged: (value) => setState(() => _unit = value ?? '개'),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            DropdownButtonFormField<String>(
              initialValue: _category,
              decoration: const InputDecoration(
                labelText: '분류',
                border: OutlineInputBorder(),
              ),
              items: _categories
                  .map(
                    (value) =>
                        DropdownMenuItem(value: value, child: Text(value)),
                  )
                  .toList(),
              onChanged: (value) => setState(() => _category = value ?? '기타'),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _price,
              keyboardType: TextInputType.number,
              decoration: const InputDecoration(
                labelText: '예상 금액',
                suffixText: '원',
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _note,
              maxLines: 2,
              decoration: const InputDecoration(
                labelText: '메모',
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 18),
            FilledButton(
              onPressed: _submit,
              child: Text(widget.item == null ? '추가하기' : '저장하기'),
            ),
          ],
        ),
      ),
    );
  }
}

class _ShoppingDraft {
  const _ShoppingDraft({
    required this.name,
    required this.quantity,
    required this.unit,
    required this.category,
    required this.estimatedPrice,
    this.note,
  });
  final String name;
  final double quantity;
  final String unit;
  final String category;
  final int estimatedPrice;
  final String? note;
}

class _EmptyShoppingList extends StatelessWidget {
  const _EmptyShoppingList({required this.filter});
  final _ShoppingFilter filter;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.shopping_basket_outlined, size: 58),
            const SizedBox(height: 14),
            Text(
              filter == _ShoppingFilter.completed
                  ? '아직 구매 완료한 항목이 없습니다.'
                  : '장보기 목록이 비어 있습니다.',
            ),
          ],
        ),
      ),
    );
  }
}

String _won(int value) {
  final formatted = value.toString().replaceAllMapped(
    RegExp(r'(\d)(?=(\d{3})+(?!\d))'),
    (match) => '${match[1]},',
  );
  return '$formatted원';
}
