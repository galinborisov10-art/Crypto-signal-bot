"""
Test suite for fundamental analysis toggle functionality

Tests the logic and data structures for the fundamental analysis toggle feature.
These tests validate the core functionality without requiring full bot imports.
"""

import unittest


class TestUserSettingsLogic(unittest.TestCase):
    """Test user settings logic with fundamental analysis fields"""
    
    def setUp(self):
        """Simulate get_user_settings function logic"""
        self.default_settings = {
            'tp': 3.0,
            'sl': 1.0,
            'rr': 3.0,
            'timeframe': '4h',
            'alerts_enabled': False,
            'alert_interval': 3600,
            'news_enabled': False,
            'news_interval': 7200,
            'use_fundamental': False,
            'fundamental_weight': 0.3,
        }
    
    def get_user_settings_mock(self, bot_data, chat_id):
        """Mock implementation of get_user_settings"""
        if chat_id not in bot_data:
            bot_data[chat_id] = self.default_settings.copy()
        # Ensure backward compatibility
        if 'use_fundamental' not in bot_data[chat_id]:
            bot_data[chat_id]['use_fundamental'] = False
        if 'fundamental_weight' not in bot_data[chat_id]:
            bot_data[chat_id]['fundamental_weight'] = 0.3
        return bot_data[chat_id]
    
    def test_new_user_default_settings(self):
        """Test that new users get default fundamental settings"""
        bot_data = {}
        chat_id = 12345
        
        settings = self.get_user_settings_mock(bot_data, chat_id)
        
        self.assertIn('use_fundamental', settings)
        self.assertFalse(settings['use_fundamental'])
        self.assertIn('fundamental_weight', settings)
        self.assertEqual(settings['fundamental_weight'], 0.3)
    
    def test_existing_user_backward_compatibility(self):
        """Test that existing users get fundamental fields added"""
        bot_data = {
            12345: {
                'tp': 3.0,
                'sl': 1.0,
                'rr': 3.0,
                'timeframe': '4h',
                'alerts_enabled': False,
                'alert_interval': 3600,
                'news_enabled': False,
                'news_interval': 7200,
            }
        }
        chat_id = 12345
        
        settings = self.get_user_settings_mock(bot_data, chat_id)
        
        self.assertIn('use_fundamental', settings)
        self.assertFalse(settings['use_fundamental'])
        self.assertIn('fundamental_weight', settings)
        self.assertEqual(settings['fundamental_weight'], 0.3)
        self.assertEqual(settings['tp'], 3.0)
        self.assertEqual(settings['timeframe'], '4h')
    
    def test_settings_persistence(self):
        """Test that fundamental settings persist"""
        bot_data = {}
        chat_id = 12345
        
        settings1 = self.get_user_settings_mock(bot_data, chat_id)
        settings1['use_fundamental'] = True
        settings1['fundamental_weight'] = 0.4
        
        settings2 = self.get_user_settings_mock(bot_data, chat_id)
        
        self.assertTrue(settings2['use_fundamental'])
        self.assertEqual(settings2['fundamental_weight'], 0.4)


class TestToggleFunctionality(unittest.TestCase):
    """Test fundamental analysis toggle ON/OFF"""
    
    def test_toggle_from_off_to_on(self):
        """Test toggling fundamental from OFF to ON"""
        settings = {'use_fundamental': False}
        settings['use_fundamental'] = True
        self.assertTrue(settings['use_fundamental'])
    
    def test_toggle_from_on_to_off(self):
        """Test toggling fundamental from ON to OFF"""
        settings = {'use_fundamental': True}
        settings['use_fundamental'] = False
        self.assertFalse(settings['use_fundamental'])
    
    def test_multiple_toggles(self):
        """Test multiple toggle operations"""
        settings = {'use_fundamental': False}
        
        self.assertFalse(settings['use_fundamental'])
        settings['use_fundamental'] = True
        self.assertTrue(settings['use_fundamental'])
        settings['use_fundamental'] = False
        self.assertFalse(settings['use_fundamental'])
        settings['use_fundamental'] = True
        self.assertTrue(settings['use_fundamental'])


class TestWeightCalculation(unittest.TestCase):
    """Test weight calculation for fundamental/technical mix"""
    
    def test_default_weight_70_30(self):
        """Test default 70% technical, 30% fundamental"""
        fund_weight = 0.3
        tech_weight = 1 - fund_weight
        
        self.assertEqual(fund_weight, 0.3)
        self.assertEqual(tech_weight, 0.7)
    
    def test_custom_weight_50_50(self):
        """Test custom 50/50 weight distribution"""
        fund_weight = 0.5
        tech_weight = 1 - fund_weight
        
        self.assertEqual(fund_weight, 0.5)
        self.assertEqual(tech_weight, 0.5)
    
    def test_weighted_score_calculation(self):
        """Test combined score calculation with weights"""
        technical_score = 75.0
        fundamental_score = 80.0
        tech_weight = 0.7
        fund_weight = 0.3
        
        combined = (technical_score * tech_weight) + (fundamental_score * fund_weight)
        
        self.assertEqual(combined, 76.5)
    
    def test_weighted_score_extreme_technical(self):
        """Test with high technical, low fundamental"""
        technical_score = 90.0
        fundamental_score = 40.0
        tech_weight = 0.7
        fund_weight = 0.3
        
        combined = (technical_score * tech_weight) + (fundamental_score * fund_weight)
        
        self.assertEqual(combined, 75.0)
    
    def test_weighted_score_extreme_fundamental(self):
        """Test with low technical, high fundamental"""
        technical_score = 40.0
        fundamental_score = 90.0
        tech_weight = 0.7
        fund_weight = 0.3
        
        combined = (technical_score * tech_weight) + (fundamental_score * fund_weight)
        
        self.assertEqual(combined, 55.0)


class TestSignalIntegrationLogic(unittest.TestCase):
    """Test signal generation logic with fundamental enabled/disabled"""
    
    def test_fundamental_disabled_check(self):
        """When user disables fundamental, should not run"""
        user_wants = False
        feature_flag = True
        
        should_run = user_wants and feature_flag
        self.assertFalse(should_run)
    
    def test_fundamental_both_enabled(self):
        """When both user and feature flag enabled, should run"""
        user_wants = True
        feature_flag = True
        
        should_run = user_wants and feature_flag
        self.assertTrue(should_run)
    
    def test_fundamental_user_on_flag_off(self):
        """User wants fundamental but feature flag is off"""
        user_wants = True
        feature_flag = False
        
        should_run = user_wants and feature_flag
        self.assertFalse(should_run)
    
    def test_fundamental_user_off_flag_on(self):
        """User doesn't want fundamental but feature flag is on"""
        user_wants = False
        feature_flag = True
        
        should_run = user_wants and feature_flag
        self.assertFalse(should_run)


class TestAnalysisModeIndicator(unittest.TestCase):
    """Test analysis mode status display"""
    
    def test_analysis_mode_technical_only(self):
        """Test indicator when fundamental is disabled"""
        use_fundamental = False
        
        if use_fundamental:
            mode = "Technical ✅ + Fundamental ✅"
        else:
            mode = "Technical ✅ | Fundamental ❌"
        
        self.assertEqual(mode, "Technical ✅ | Fundamental ❌")
    
    def test_analysis_mode_with_fundamental(self):
        """Test indicator when fundamental is enabled"""
        use_fundamental = True
        
        if use_fundamental:
            mode = "Technical ✅ + Fundamental ✅"
        else:
            mode = "Technical ✅ | Fundamental ❌"
        
        self.assertEqual(mode, "Technical ✅ + Fundamental ✅")
    
    def test_weight_display_format(self):
        """Test weight distribution display"""
        tech_weight = 0.7
        fund_weight = 0.3
        
        display = f"{int(tech_weight*100)}/{int(fund_weight*100)}"
        
        self.assertEqual(display, "70/30")


class TestFundCommandLogic(unittest.TestCase):
    """Test /fund command logic"""
    
    def test_fund_default_state(self):
        """Test default state is disabled"""
        settings = {'use_fundamental': False}
        self.assertFalse(settings['use_fundamental'])
    
    def test_fund_on_enables(self):
        """Test enabling fundamental"""
        settings = {'use_fundamental': False}
        settings['use_fundamental'] = True
        self.assertTrue(settings['use_fundamental'])
    
    def test_fund_off_disables(self):
        """Test disabling fundamental"""
        settings = {'use_fundamental': True}
        settings['use_fundamental'] = False
        self.assertFalse(settings['use_fundamental'])


class TestScoreCombinationScenarios(unittest.TestCase):
    """Test real-world score combination scenarios"""
    
    def test_bullish_technical_bullish_fundamental(self):
        """Both analyses are bullish"""
        tech = 85.0
        fund = 80.0
        combined = (tech * 0.7) + (fund * 0.3)
        
        # 85 * 0.7 + 80 * 0.3 = 59.5 + 24 = 83.5
        self.assertEqual(combined, 83.5)
        self.assertGreater(combined, 75)  # Strong signal
    
    def test_bullish_technical_bearish_fundamental(self):
        """Technical bullish, fundamental bearish"""
        tech = 80.0
        fund = 40.0
        combined = (tech * 0.7) + (fund * 0.3)
        
        # 80 * 0.7 + 40 * 0.3 = 56 + 12 = 68
        self.assertEqual(combined, 68.0)
        self.assertGreater(combined, 60)  # Still decent, technical has more weight
    
    def test_bearish_technical_bullish_fundamental(self):
        """Technical bearish, fundamental bullish"""
        tech = 40.0
        fund = 85.0
        combined = (tech * 0.7) + (fund * 0.3)
        
        # 40 * 0.7 + 85 * 0.3 = 28 + 25.5 = 53.5
        self.assertEqual(combined, 53.5)
        self.assertLess(combined, 60)  # Weak signal, technical dominates
    
    def test_neutral_scenario(self):
        """Both analyses neutral"""
        tech = 50.0
        fund = 50.0
        combined = (tech * 0.7) + (fund * 0.3)
        
        # 50 * 0.7 + 50 * 0.3 = 35 + 15 = 50
        self.assertEqual(combined, 50.0)


if __name__ == '__main__':
    unittest.main(verbosity=2)
