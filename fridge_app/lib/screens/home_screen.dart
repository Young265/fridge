import 'package:flutter/material.dart';

import '../models/app_user.dart';
import '../models/fridge.dart';
import 'inventory/inventory_screen.dart';
import 'recipes/recipe_list_screen.dart';

class HomeScreen extends StatelessWidget {
  const HomeScreen({
    super.key,
    required this.user,
    required this.fridge,
    required this.onChangeFridge,
    required this.onLogout,
  });

  final AppUser user;
  final Fridge fridge;
  final VoidCallback onChangeFridge;
  final VoidCallback onLogout;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(fridge.fridgeName),
        actions: [
          TextButton(onPressed: onChangeFridge, child: const Text('냉장고 변경')),
          IconButton(onPressed: onLogout, icon: const Icon(Icons.logout)),
        ],
      ),
      body: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              '${user.name}님, 무엇을 확인할까요?',
              style: Theme.of(context).textTheme.headlineSmall,
            ),
            const SizedBox(height: 8),
            Text(
              '현재 선택한 냉장고: ${fridge.fridgeName}',
              style: Theme.of(context).textTheme.bodyLarge,
            ),
            const SizedBox(height: 24),
            Expanded(
              child: LayoutBuilder(
                builder: (context, constraints) {
                  final isWide = constraints.maxWidth > 720;
                  return GridView.count(
                    crossAxisCount: isWide ? 2 : 1,
                    crossAxisSpacing: 16,
                    mainAxisSpacing: 16,
                    childAspectRatio: isWide ? 1.45 : 1.9,
                    children: [
                      _HomeCard(
                        title: '재고 확인',
                        subtitle: '냉장고 안의 재료를 한눈에 보고 상세 정보를 확인할 수 있어요.',
                        icon: Icons.inventory_2_rounded,
                        color: const Color(0xFF2E7D32),
                        onTap: () {
                          Navigator.of(context).push(
                            MaterialPageRoute(
                              builder: (_) => InventoryScreen(fridge: fridge),
                            ),
                          );
                        },
                      ),
                      _HomeCard(
                        title: '레시피 확인',
                        subtitle: '현재 재료 기준으로 부족한 재료가 가장 적은 레시피를 추천합니다.',
                        icon: Icons.menu_book_rounded,
                        color: const Color(0xFFEF6C00),
                        onTap: () {
                          Navigator.of(context).push(
                            MaterialPageRoute(
                              builder: (_) => RecipeListScreen(fridge: fridge),
                            ),
                          );
                        },
                      ),
                    ],
                  );
                },
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _HomeCard extends StatelessWidget {
  const _HomeCard({
    required this.title,
    required this.subtitle,
    required this.icon,
    required this.color,
    required this.onTap,
  });

  final String title;
  final String subtitle;
  final IconData icon;
  final Color color;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(28),
      child: Ink(
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(28),
          gradient: LinearGradient(
            colors: [color, color.withValues(alpha: 0.72)],
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
          ),
        ),
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Icon(icon, size: 42, color: Colors.white),
              const Spacer(),
              Text(
                title,
                style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                  color: Colors.white,
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: 8),
              Text(
                subtitle,
                style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                  color: Colors.white.withValues(alpha: 0.92),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
