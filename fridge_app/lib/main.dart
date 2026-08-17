import 'package:flutter/material.dart';

import 'models/app_user.dart';
import 'models/fridge.dart';
import 'screens/auth/login_screen.dart';
import 'screens/auth/register_screen.dart';
import 'screens/fridge_selection_screen.dart';
import 'screens/home_screen.dart';

void main() {
  runApp(const FridgeApp());
}

class FridgeApp extends StatefulWidget {
  const FridgeApp({super.key});

  @override
  State<FridgeApp> createState() => _FridgeAppState();
}

class _FridgeAppState extends State<FridgeApp> {
  AppUser? _user;
  List<Fridge> _fridges = const [];
  Fridge? _selectedFridge;
  bool _showRegister = false;

  void _handleAuthSuccess(AppUser user, List<Fridge> fridges) {
    Fridge? selected;
    if (user.currentFridgeId != null) {
      for (final fridge in fridges) {
        if (fridge.fridgeId == user.currentFridgeId) {
          selected = fridge;
          break;
        }
      }
    }
    setState(() {
      _user = user;
      _fridges = fridges;
      _selectedFridge = selected ?? (fridges.isNotEmpty ? fridges.first : null);
      _showRegister = false;
    });
  }

  void _handleFridgesChanged(List<Fridge> fridges, {Fridge? selectedFridge}) {
    final currentId = _selectedFridge?.fridgeId;
    Fridge? preserved;
    if (currentId != null) {
      for (final fridge in fridges) {
        if (fridge.fridgeId == currentId) {
          preserved = fridge;
          break;
        }
      }
    }
    setState(() {
      _fridges = fridges;
      _selectedFridge =
          selectedFridge ??
          preserved ??
          (fridges.isNotEmpty ? fridges.first : null);
    });
  }

  void _logout() {
    setState(() {
      _user = null;
      _fridges = const [];
      _selectedFridge = null;
      _showRegister = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      title: '스마트 냉장고',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xFF2F6B4F)),
        scaffoldBackgroundColor: const Color(0xFFF7F8F5),
        appBarTheme: const AppBarTheme(
          backgroundColor: Color(0xFFF7F8F5),
          surfaceTintColor: Colors.transparent,
          centerTitle: false,
        ),
        cardTheme: const CardThemeData(
          color: Colors.white,
          margin: EdgeInsets.zero,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.all(Radius.circular(16)),
          ),
        ),
        useMaterial3: true,
      ),
      home: _buildHome(),
    );
  }

  Widget _buildHome() {
    if (_user == null) {
      if (_showRegister) {
        return RegisterScreen(
          onRegistered: _handleAuthSuccess,
          onShowLogin: () {
            setState(() {
              _showRegister = false;
            });
          },
        );
      }
      return LoginScreen(
        onLoggedIn: _handleAuthSuccess,
        onShowRegister: () {
          setState(() {
            _showRegister = true;
          });
        },
      );
    }

    if (_selectedFridge == null) {
      return FridgeSelectionScreen(
        user: _user!,
        fridges: _fridges,
        onSelected: (fridge) {
          setState(() {
            _selectedFridge = fridge;
          });
        },
        onFridgesChanged: _handleFridgesChanged,
        onLogout: _logout,
      );
    }

    return HomeScreen(
      user: _user!,
      fridge: _selectedFridge!,
      onChangeFridge: () {
        setState(() {
          _selectedFridge = null;
        });
      },
      onLogout: _logout,
    );
  }
}
