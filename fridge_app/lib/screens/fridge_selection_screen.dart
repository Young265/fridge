import 'package:flutter/material.dart';

import '../models/app_user.dart';
import '../models/fridge.dart';
import '../services/api_service.dart';

class FridgeSelectionScreen extends StatefulWidget {
  const FridgeSelectionScreen({
    super.key,
    required this.user,
    required this.fridges,
    required this.onSelected,
    required this.onFridgesChanged,
    required this.onLogout,
  });

  final AppUser user;
  final List<Fridge> fridges;
  final ValueChanged<Fridge> onSelected;
  final void Function(List<Fridge> fridges, {Fridge? selectedFridge})
  onFridgesChanged;
  final VoidCallback onLogout;

  @override
  State<FridgeSelectionScreen> createState() => _FridgeSelectionScreenState();
}

class _FridgeSelectionScreenState extends State<FridgeSelectionScreen> {
  late List<Fridge> _fridges;

  @override
  void initState() {
    super.initState();
    _fridges = List<Fridge>.from(widget.fridges);
  }

  Future<void> _createFridge() async {
    final controller = TextEditingController();
    final name = await showDialog<String>(
      context: context,
      builder: (context) {
        return AlertDialog(
          title: const Text('냉장고 추가'),
          content: TextField(
            controller: controller,
            decoration: const InputDecoration(
              labelText: '냉장고 이름',
              border: OutlineInputBorder(),
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(context).pop(),
              child: const Text('취소'),
            ),
            FilledButton(
              onPressed: () =>
                  Navigator.of(context).pop(controller.text.trim()),
              child: const Text('추가'),
            ),
          ],
        );
      },
    );
    controller.dispose();

    if (name == null || name.isEmpty) {
      return;
    }

    try {
      final fridge = await ApiService.createFridge(
        userId: widget.user.userId,
        fridgeName: name,
      );
      final updated = [..._fridges, fridge];
      setState(() {
        _fridges = updated;
      });
      widget.onFridgesChanged(
        updated,
        selectedFridge: _fridges.length == 1 ? fridge : null,
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
    }
  }

  Future<void> _deleteFridge(Fridge fridge) async {
    final confirmed =
        await showDialog<bool>(
          context: context,
          builder: (context) {
            return AlertDialog(
              title: const Text('냉장고 삭제'),
              content: Text('${fridge.fridgeName}을(를) 삭제할까요?'),
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
      await ApiService.deleteFridge(fridge.fridgeId);
      final updated = _fridges
          .where((item) => item.fridgeId != fridge.fridgeId)
          .toList();
      setState(() {
        _fridges = updated;
      });
      widget.onFridgesChanged(
        updated,
        selectedFridge: updated.isNotEmpty ? updated.first : null,
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
    }
  }

  Future<void> _selectFridge(BuildContext context, Fridge fridge) async {
    try {
      await ApiService.updateCurrentFridge(
        userId: widget.user.userId,
        fridgeId: fridge.fridgeId,
      );
      if (!context.mounted) {
        return;
      }
      widget.onSelected(fridge);
    } catch (error) {
      if (!context.mounted) {
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
    return Scaffold(
      appBar: AppBar(
        title: const Text('냉장고 변경'),
        actions: [
          IconButton(
            onPressed: widget.onLogout,
            icon: const Icon(Icons.logout),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _createFridge,
        icon: const Icon(Icons.add),
        label: const Text('냉장고 추가'),
      ),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: _fridges.isEmpty
            ? const Center(child: Text('등록된 냉장고가 없습니다. 새 냉장고를 추가해 주세요.'))
            : ListView.separated(
                itemCount: _fridges.length,
                separatorBuilder: (context, index) =>
                    const SizedBox(height: 12),
                itemBuilder: (context, index) {
                  final fridge = _fridges[index];
                  return Card(
                    child: ListTile(
                      leading: const CircleAvatar(
                        child: Icon(Icons.kitchen_rounded),
                      ),
                      title: Text(fridge.fridgeName),
                      subtitle: Text('생성일 ${fridge.createdAt}'),
                      trailing: IconButton(
                        onPressed: () => _deleteFridge(fridge),
                        icon: const Icon(Icons.delete_outline),
                      ),
                      onTap: () => _selectFridge(context, fridge),
                    ),
                  );
                },
              ),
      ),
    );
  }
}
