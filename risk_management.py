"""
🛡️ Risk Management System
Управление на риска при търговия
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

class RiskManager:
    """Управлява риска и проверява trade safety"""
    
    def __init__(self, config_file: str = "risk_config.json"):
        self.config_file = config_file
        self.config = self.load_config()
        
    def load_config(self) -> Dict:
        """Зарежда risk configuration"""
        default_config = {
            "max_position_size_pct": 20.0,      # Макс 20% от портфейла в 1 trade
            "max_daily_loss_pct": 6.0,           # Макс 6% загуба на ден
            "max_concurrent_trades": 5,          # Макс 5 паралелни trades
            "min_risk_reward_ratio": 2.0,        # Минимум 1:2 (за $1 риск, $2 печалба)
            "risk_per_trade_pct": 2.0,           # Риск 2% на trade
            "portfolio_balance": 1000.0,         # Начален баланс (user set)
            "stop_trading_on_daily_limit": True  # Спри при дневен лимит
        }
        
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    default_config.update(loaded)
            except:
                pass
        else:
            self.save_config(default_config)
            
        return default_config
    
    def save_config(self, config: Dict):
        """Запазва configuration"""
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    
    def update_portfolio_balance(self, new_balance: float):
        """Обновява portfolio баланса"""
        self.config['portfolio_balance'] = new_balance
        self.save_config(self.config)
    
    def calculate_position_size(self, entry_price: float, stop_loss_price: float) -> Tuple[float, str]:
        """
        Изчислява оптималния размер на позицията
        
        Returns:
            (position_size, reasoning)
        """
        portfolio = self.config['portfolio_balance']
        risk_pct = self.config['risk_per_trade_pct'] / 100
        max_position_pct = self.config['max_position_size_pct'] / 100
        
        # Максимална загуба на trade
        max_loss = portfolio * risk_pct
        
        # SL разстояние в %
        sl_distance_pct = abs(entry_price - stop_loss_price) / entry_price
        
        # Position size базиран на риск
        position_size = max_loss / sl_distance_pct
        
        # Cap на макс % от портфейла
        max_allowed = portfolio * max_position_pct
        if position_size > max_allowed:
            position_size = max_allowed
            reason = f"⚠️ Position capped at {max_position_pct*100}% of portfolio"
        else:
            reason = f"✅ Position sized for {risk_pct*100}% risk"
        
        return round(position_size, 2), reason
    
    def check_risk_reward(self, entry: float, tp: float, sl: float, signal: str) -> Tuple[bool, float, str]:
        """
        Проверява Risk/Reward ratio
        
        Returns:
            (is_valid, actual_ratio, message)
        """
        min_ratio = self.config['min_risk_reward_ratio']
        
        if signal == 'BUY':
            risk = entry - sl
            reward = tp - entry
        else:  # SELL
            risk = sl - entry
            reward = entry - tp
        
        if risk <= 0:
            return False, 0, "❌ Invalid SL (must be below/above entry)"
        
        ratio = reward / risk
        
        if ratio >= min_ratio:
            return True, ratio, f"✅ R:R = 1:{ratio:.2f} (min 1:{min_ratio})"
        else:
            return False, ratio, f"❌ R:R = 1:{ratio:.2f} too low (min 1:{min_ratio})"
    
    def check_daily_loss_limit(self, journal_file: str = "trading_journal.json") -> Tuple[bool, float, str]:
        """
        Проверява дали дневният loss лимит е достигнат
        
        Returns:
            (can_trade, daily_loss_pct, message)
        """
        if not os.path.exists(journal_file):
            return True, 0.0, "✅ No trades today"
        
        try:
            with open(journal_file, 'r', encoding='utf-8') as f:
                journal = json.load(f)
        except:
            return True, 0.0, "✅ No trades today"
        
        # Филтрирай trades от днес
        today = datetime.now().strftime('%Y-%m-%d')
        today_trades = [t for t in journal if t.get('timestamp', '').startswith(today) 
                       and t.get('status') in ['WIN', 'LOSS']]
        
        if not today_trades:
            return True, 0.0, "✅ No closed trades today"
        
        # Изчисли дневна загуба
        total_profit_loss = sum(t.get('profit_loss_pct', 0) for t in today_trades)
        
        max_daily_loss = self.config['max_daily_loss_pct']
        
        if abs(total_profit_loss) >= max_daily_loss and total_profit_loss < 0:
            return False, total_profit_loss, f"🛑 Daily loss limit reached: {total_profit_loss:.2f}%"
        else:
            return True, total_profit_loss, f"✅ Daily P/L: {total_profit_loss:+.2f}% (limit: -{max_daily_loss}%)"
    
    def check_concurrent_trades(self, journal_file: str = "trading_journal.json") -> Tuple[bool, int, str]:
        """
        Проверява броя активни trades
        
        Returns:
            (can_open, active_count, message)
        """
        if not os.path.exists(journal_file):
            return True, 0, "✅ No active trades"
        
        try:
            with open(journal_file, 'r', encoding='utf-8') as f:
                journal = json.load(f)
        except:
            return True, 0, "✅ No active trades"
        
        # Брой PENDING trades
        active = [t for t in journal if t.get('status') == 'PENDING']
        active_count = len(active)
        
        max_concurrent = self.config['max_concurrent_trades']
        
        if active_count >= max_concurrent:
            return False, active_count, f"🛑 Max concurrent trades ({max_concurrent}) reached"
        else:
            return True, active_count, f"✅ Active trades: {active_count}/{max_concurrent}"
    
    def validate_trade(self, entry: float, tp: float, sl: float, signal: str, 
                      journal_file: str = "trading_journal.json") -> Dict:
        """
        Пълна проверка на trade преди изпълнение
        
        Returns dict with:
            - approved: bool
            - position_size: float
            - risk_reward: float
            - warnings: list
            - errors: list
        """
        warnings = []
        errors = []
        
        # 1. Check Risk/Reward
        rr_valid, rr_ratio, rr_msg = self.check_risk_reward(entry, tp, sl, signal)
        if not rr_valid:
            errors.append(rr_msg)
        else:
            warnings.append(rr_msg)
        
        # 2. Check Daily Loss Limit
        can_trade_daily, daily_pl, daily_msg = self.check_daily_loss_limit(journal_file)
        if not can_trade_daily:
            errors.append(daily_msg)
        else:
            warnings.append(daily_msg)
        
        # 3. Check Concurrent Trades
        can_open, active, concurrent_msg = self.check_concurrent_trades(journal_file)
        if not can_open:
            errors.append(concurrent_msg)
        else:
            warnings.append(concurrent_msg)
        
        # 4. Calculate Position Size
        position_size, size_msg = self.calculate_position_size(entry, sl)
        warnings.append(size_msg)
        
        return {
            'approved': len(errors) == 0,
            'position_size': position_size,
            'position_size_usd': position_size,
            'risk_reward_ratio': rr_ratio,
            'daily_pnl_pct': daily_pl,
            'active_trades': active,
            'warnings': warnings,
            'errors': errors
        }
    
    def get_settings_summary(self) -> str:
        """Връща текстово описание на настройките"""
        cfg = self.config
        return f"""
🛡️ <b>RISK MANAGEMENT SETTINGS</b>

💰 <b>Portfolio:</b> ${cfg['portfolio_balance']:.2f}
📊 <b>Risk per trade:</b> {cfg['risk_per_trade_pct']}%
📈 <b>Max position size:</b> {cfg['max_position_size_pct']}%
🔴 <b>Daily loss limit:</b> {cfg['max_daily_loss_pct']}%
🔢 <b>Max concurrent trades:</b> {cfg['max_concurrent_trades']}
⚖️ <b>Min Risk/Reward:</b> 1:{cfg['min_risk_reward_ratio']}
🛑 <b>Auto-stop on limit:</b> {'✅ Yes' if cfg['stop_trading_on_daily_limit'] else '❌ No'}
"""


# Singleton instance
_risk_manager = None

def get_risk_manager() -> RiskManager:
    """Връща global Risk Manager instance"""
    global _risk_manager
    if _risk_manager is None:
        _risk_manager = RiskManager()
    return _risk_manager
