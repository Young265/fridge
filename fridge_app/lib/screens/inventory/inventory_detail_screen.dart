import 'package:flutter/material.dart';

import '../../models/inventory_item.dart';
import '../../services/api_service.dart';

class InventoryDetailScreen extends StatefulWidget {
  const InventoryDetailScreen({super.key, required this.fridgeId, this.item});

  final int fridgeId;
  final InventoryItem? item;

  @override
  State<InventoryDetailScreen> createState() => _InventoryDetailScreenState();
}

class _InventoryDetailScreenState extends State<InventoryDetailScreen> {
  final _formKey = GlobalKey<FormState>();
  late final TextEditingController _nameController;
  late final TextEditingController _quantityController;
  late final TextEditingController _unitController;
  late final TextEditingController _noteController;
  late String _status;
  bool _isSaving = false;

  bool get _isEdit => widget.item != null;

  @override
  void initState() {
    super.initState();
    _nameController = TextEditingController(
      text: widget.item?.displayName ?? '',
    );
    _quantityController = TextEditingController(
      text: widget.item != null ? widget.item!.quantity.toString() : '1',
    );
    _unitController = TextEditingController(
      text: widget.item?.unitLabel ?? '개',
    );
    _noteController = TextEditingController(text: widget.item?.note ?? '');
    _status = widget.item?.status ?? 'USER_CONFIRMED';
  }

  @override
  void dispose() {
    _nameController.dispose();
    _quantityController.dispose();
    _unitController.dispose();
    _noteController.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    if (!_formKey.currentState!.validate()) {
      return;
    }

    setState(() {
      _isSaving = true;
    });

    try {
      final quantity = double.tryParse(_quantityController.text.trim()) ?? 1;
      final unit = _unitController.text.trim().isEmpty
          ? '개'
          : _unitController.text.trim();
      if (_isEdit) {
        await ApiService.updateInventoryItem(
          fridgeItemId: widget.item!.fridgeItemId,
          displayName: _nameController.text.trim(),
          quantity: quantity,
          unit: unit,
          status: _status,
          note: _noteController.text.trim(),
        );
      } else {
        await ApiService.createInventoryItem(
          fridgeId: widget.fridgeId,
          displayName: _nameController.text.trim(),
          quantity: quantity,
          unit: unit,
          status: _status,
          note: _noteController.text.trim(),
        );
      }

      if (!mounted) {
        return;
      }
      Navigator.of(context).pop(true);
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
        setState(() {
          _isSaving = false;
        });
      }
    }
  }

  Future<void> _delete() async {
    if (!_isEdit) {
      return;
    }

    final confirmed =
        await showDialog<bool>(
          context: context,
          builder: (context) {
            return AlertDialog(
              title: const Text('재료 삭제'),
              content: Text('${widget.item!.displayName}을(를) 삭제할까요?'),
              actions: [
                TextButton(
                  onPressed: () => Navigator.of(context).pop(false),
                  child: const Text('취소'),
                ),
                FilledButton(
                  onPressed: () => Navigator.of(context).pop(true),
                  child: const Text('삭제'),
                ),
              ],
            );
          },
        ) ??
        false;

    if (!confirmed) {
      return;
    }

    try {
      await ApiService.deleteInventoryItem(widget.item!.fridgeItemId);
      if (!mounted) {
        return;
      }
      Navigator.of(context).pop(true);
    } catch (error) {
      if (!mounted) {
        return;
      }
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(error.toString().replaceFirst('Exception: ', '')),
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final item = widget.item;
    final imageUrl = item?.cropImageUrl ?? item?.imageUrl;

    return Scaffold(
      appBar: AppBar(
        title: Text(_isEdit ? '재료 상세' : '재료 추가'),
        actions: [
          if (_isEdit)
            IconButton(
              onPressed: _delete,
              icon: const Icon(Icons.delete_outline),
            ),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              if (imageUrl != null && imageUrl.isNotEmpty)
                ClipRRect(
                  borderRadius: BorderRadius.circular(24),
                  child: Image.network(
                    imageUrl,
                    height: 220,
                    fit: BoxFit.cover,
                    errorBuilder: (context, error, stackTrace) =>
                        const SizedBox.shrink(),
                  ),
                ),
              if (item != null && item.needsReview) ...[
                const SizedBox(height: 12),
                Container(
                  padding: const EdgeInsets.all(14),
                  decoration: BoxDecoration(
                    color: const Color(0xFFFFF3E0),
                    borderRadius: BorderRadius.circular(16),
                  ),
                  child: Text(
                    'AI가 확정하지 못한 항목입니다. 이름과 상태를 수정해서 반영할 수 있습니다.',
                    style: Theme.of(context).textTheme.bodyMedium,
                  ),
                ),
              ],
              const SizedBox(height: 20),
              TextFormField(
                controller: _nameController,
                decoration: const InputDecoration(
                  labelText: '재료 이름',
                  border: OutlineInputBorder(),
                ),
                validator: (value) {
                  if (value == null || value.trim().isEmpty) {
                    return '재료 이름을 입력해 주세요.';
                  }
                  return null;
                },
              ),
              const SizedBox(height: 16),
              Row(
                children: [
                  Expanded(
                    child: TextFormField(
                      controller: _quantityController,
                      keyboardType: const TextInputType.numberWithOptions(
                        decimal: true,
                      ),
                      decoration: const InputDecoration(
                        labelText: '수량',
                        border: OutlineInputBorder(),
                      ),
                      validator: (value) {
                        if (value == null ||
                            double.tryParse(value.trim()) == null) {
                          return '숫자를 입력해 주세요.';
                        }
                        return null;
                      },
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: TextFormField(
                      controller: _unitController,
                      decoration: const InputDecoration(
                        labelText: '단위',
                        border: OutlineInputBorder(),
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 16),
              DropdownButtonFormField<String>(
                initialValue: _status,
                decoration: const InputDecoration(
                  labelText: '상태',
                  border: OutlineInputBorder(),
                ),
                items: const [
                  DropdownMenuItem(
                    value: 'USER_CONFIRMED',
                    child: Text('사용자 확인 완료'),
                  ),
                  DropdownMenuItem(
                    value: 'RECOGNIZED',
                    child: Text('AI 인식 완료'),
                  ),
                  DropdownMenuItem(value: 'UNRECOGNIZED', child: Text('확인 필요')),
                ],
                onChanged: (value) {
                  if (value != null) {
                    setState(() {
                      _status = value;
                    });
                  }
                },
              ),
              const SizedBox(height: 16),
              TextFormField(
                controller: _noteController,
                maxLines: 3,
                decoration: const InputDecoration(
                  labelText: '메모',
                  border: OutlineInputBorder(),
                ),
              ),
              if (item != null) ...[
                const SizedBox(height: 16),
                Text('최초 등록: ${item.createdAt}'),
                const SizedBox(height: 4),
                Text('마지막 수정: ${item.updatedAt}'),
                if (item.detectedName != null) ...[
                  const SizedBox(height: 4),
                  Text('AI 추정값: ${item.detectedName}'),
                ],
              ],
              const SizedBox(height: 24),
              FilledButton(
                onPressed: _isSaving ? null : _save,
                child: _isSaving
                    ? const SizedBox(
                        height: 20,
                        width: 20,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Text('저장'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
