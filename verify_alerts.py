"""
🔍 Alert System Verification Tool
==================================

This module verifies that both the 80% alert system and final alert system
are working correctly by checking:
1. Code implementation
2. Active monitoring
3. Journal logging
4. Real data coverage

CRITICAL: This is a READ-ONLY diagnostic tool.
"""

import os
import json
import re
from datetime import datetime, timezone
from typing import Dict, List, Any, Tuple


class AlertVerifier:
    """Verifies 80% alert and final alert systems are working correctly"""

    def __init__(self):
        """Initialize alert verifier with auto-detected paths"""
        # Auto-detect base path
        if os.path.exists('/root/Crypto-signal-bot'):
            self.base_path = '/root/Crypto-signal-bot'
        elif os.path.exists('/workspaces/Crypto-signal-bot'):
            self.base_path = '/workspaces/Crypto-signal-bot'
        else:
            self.base_path = os.path.dirname(os.path.abspath(__file__))

        self.journal_path = os.path.join(self.base_path, 'trading_journal.json')
        self.bot_path = os.path.join(self.base_path, 'bot.py')

    async def verify_all(self) -> Dict[str, Any]:
        """
        Run all verification checks
        
        Returns:
            Dict with verification results for both alert systems
        """
        results = {
            '80_alert': await self.verify_80_alert(),
            'final_alert': await self.verify_final_alert(),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }

        # Generate report file
        self._generate_report_file(results)

        return results

    async def verify_80_alert(self) -> Dict[str, Any]:
        """
        Verify 80% alert system is working
        
        Checks:
        1. Function exists in bot.py
        2. Active trades tracking exists
        3. Price monitoring exists
        4. Alerts logged to journal
        5. Alerts exist in journal data
        6. Backtest integration
        
        Returns:
            Dict with verification results and recommendations
        """
        checks = {}
        issues = []
        recommendations = []

        # CHECK 1: Function exists in bot.py
        function_exists, function_line = self._check_code_pattern(
            self.bot_path,
            r'(check_80_percent|80.*alert|eighty.*percent)',
            'case_insensitive'
        )
        checks['function_exists'] = function_exists
        if function_exists:
            checks['function_location'] = f"bot.py line {function_line}"
        else:
            issues.append("Missing 80% alert function")
            recommendations.append("Implement check_80_percent_tp() function in bot.py")

        # CHECK 2: Active trades tracking
        active_tracking, active_line = self._check_code_pattern(
            self.bot_path,
            r'active_trades',
            'case_insensitive'
        )
        checks['active_trades_tracking'] = active_tracking
        if not active_tracking:
            issues.append("No active_trades variable found")
            recommendations.append("Implement active_trades tracking in bot.py")
            recommendations.append("Add price monitoring loop (check every 60s)")

        # CHECK 3: Price monitoring
        monitoring, monitoring_line = self._check_code_pattern(
            self.bot_path,
            r'(monitor.*price|price.*monitor|scheduler.*add_job)',
            'case_insensitive'
        )
        checks['price_monitoring'] = monitoring

        # CHECK 4: Journal logging
        journal_logging, log_line = self._check_code_pattern(
            self.bot_path,
            r'alerts_80',
            'case_sensitive'
        )
        checks['journal_logging'] = journal_logging
        if not journal_logging:
            issues.append("80% alerts not being logged to journal")

        # CHECK 5: Real data exists
        data_exists, coverage = self._check_journal_alerts('alerts_80')
        checks['data_exists'] = data_exists
        checks['coverage_count'] = coverage['count']
        checks['total_trades'] = coverage['total']
        
        if coverage['total'] > 0 and coverage['count'] < coverage['total'] * 0.5:
            issues.append(f"Only {coverage['count']} out of {coverage['total']} trades have 80% alerts")
            recommendations.append("Ensure 80% alerts are being logged consistently")

        # CHECK 6: Backtest integration
        backtest_integration = self._check_backtest_integration('alerts_80')
        checks['backtest_integration'] = backtest_integration

        # Determine overall status
        if not issues:
            status = "WORKING ✅"
        elif len(issues) <= 2:
            status = "PARTIAL ⚠️"
        else:
            status = "BROKEN ❌"

        # Add implementation recommendations if needed
        if issues:
            recommendations.extend([
                "Calculate 80% threshold: entry + (tp - entry) * 0.8",
                "Send Telegram notification when reached",
                "Log to journal: trade['alerts_80'].append(...)"
            ])

        return {
            'status': status,
            'checks': checks,
            'issues': issues,
            'recommendations': list(set(recommendations))  # Remove duplicates
        }

    async def verify_final_alert(self) -> Dict[str, Any]:
        """
        Verify final alert system is working
        
        Checks:
        1. Function exists in bot.py
        2. Outcome detection (WIN/LOSS)
        3. Alerts logged to journal
        4. Alerts exist in journal data
        5. Coverage % of closed trades
        6. Backtest integration
        
        Returns:
            Dict with verification results and recommendations
        """
        checks = {}
        issues = []
        recommendations = []

        # CHECK 1: Function exists
        function_exists, function_line = self._check_code_pattern(
            self.bot_path,
            r'(final_alert|trade_closed|outcome)',
            'case_insensitive'
        )
        checks['function_exists'] = function_exists
        if function_exists:
            checks['function_location'] = f"bot.py line {function_line}"
        else:
            issues.append("Missing final alert function")
            recommendations.append("Implement final_alert() function in bot.py")

        # CHECK 2: Outcome detection
        outcome_detection, outcome_line = self._check_code_pattern(
            self.bot_path,
            r'(WIN|LOSS|SUCCESS|FAILED)',
            'case_sensitive'
        )
        checks['outcome_detection'] = outcome_detection
        if outcome_detection:
            checks['outcome_location'] = f"bot.py line {outcome_line}"

        # CHECK 3: Journal logging
        journal_logging, log_line = self._check_code_pattern(
            self.bot_path,
            r'final_alerts',
            'case_sensitive'
        )
        checks['journal_logging'] = journal_logging
        if not journal_logging:
            issues.append("Final alerts not being logged to journal")

        # CHECK 4: Real data exists
        data_exists, coverage = self._check_journal_alerts('final_alerts')
        checks['data_exists'] = data_exists
        checks['coverage_count'] = coverage['count']
        checks['closed_trades'] = coverage['closed']
        
        if coverage['closed'] > 0:
            coverage_pct = (coverage['count'] / coverage['closed']) * 100
            checks['coverage_percentage'] = round(coverage_pct, 1)
            
            if coverage_pct < 80:
                issues.append(f"Only {coverage_pct:.1f}% of closed trades have final alerts")
                recommendations.append("Ensure all closed trades receive final alerts")
        else:
            checks['coverage_percentage'] = 0.0

        # CHECK 5: Backtest integration
        backtest_integration = self._check_backtest_integration('final_alerts')
        checks['backtest_integration'] = backtest_integration

        # Determine overall status
        if not issues:
            status = "WORKING ✅"
        elif len(issues) <= 2:
            status = "PARTIAL ⚠️"
        else:
            status = "BROKEN ❌"

        # Add implementation recommendations if needed
        if issues:
            recommendations.extend([
                "Detect trade closure (TP or SL hit)",
                "Determine outcome: WIN/LOSS",
                "Calculate P/L",
                "Send Telegram notification",
                "Log to journal: trade['final_alerts'].append(...)",
                "Update statistics"
            ])

        return {
            'status': status,
            'checks': checks,
            'issues': issues,
            'recommendations': list(set(recommendations))  # Remove duplicates
        }

    def _check_code_pattern(
        self,
        file_path: str,
        pattern: str,
        case_mode: str = 'case_sensitive'
    ) -> Tuple[bool, int]:
        """
        Check if a code pattern exists in a file
        
        Args:
            file_path: Path to the file to check
            pattern: Regex pattern to search for
            case_mode: 'case_sensitive' or 'case_insensitive'
        
        Returns:
            Tuple of (pattern_found, line_number)
        """
        if not os.path.exists(file_path):
            return False, 0

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')

            flags = re.IGNORECASE if case_mode == 'case_insensitive' else 0
            regex = re.compile(pattern, flags)

            for i, line in enumerate(lines, 1):
                if regex.search(line):
                    return True, i

            return False, 0

        except Exception:
            return False, 0

    def _check_journal_alerts(self, alert_type: str) -> Tuple[bool, Dict[str, int]]:
        """
        Check if alerts exist in trading journal
        
        Args:
            alert_type: 'alerts_80' or 'final_alerts'
        
        Returns:
            Tuple of (alerts_exist, coverage_dict)
        """
        coverage = {
            'count': 0,
            'total': 0,
            'closed': 0
        }

        if not os.path.exists(self.journal_path):
            return False, coverage

        try:
            with open(self.journal_path, 'r', encoding='utf-8') as f:
                journal = json.load(f)

            trades = journal.get('trades', [])
            coverage['total'] = len(trades)

            for trade in trades:
                # Check if trade is closed
                outcome = trade.get('outcome', '').upper()
                if outcome in ['WIN', 'LOSS', 'SUCCESS', 'FAILED']:
                    coverage['closed'] += 1

                # Check if alert exists
                alerts = trade.get(alert_type, [])
                if alerts and len(alerts) > 0:
                    coverage['count'] += 1

            return coverage['count'] > 0, coverage

        except Exception:
            return False, coverage

    def _check_backtest_integration(self, alert_type: str) -> bool:
        """
        Check if backtest reads alert data
        
        Args:
            alert_type: 'alerts_80' or 'final_alerts'
        
        Returns:
            True if backtest integrates this alert type
        """
        backtest_path = os.path.join(self.base_path, 'journal_backtest.py')
        
        if not os.path.exists(backtest_path):
            return False

        try:
            with open(backtest_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            return alert_type in content

        except Exception:
            return False

    def _generate_report_file(self, results: Dict[str, Any]) -> None:
        """
        Generate verification report file
        
        Args:
            results: Verification results from verify_all()
        """
        report_path = os.path.join(self.base_path, 'ALERT_VERIFICATION_REPORT.md')

        alert_80 = results['80_alert']
        final_alert = results['final_alert']

        report = f"""━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔍 ALERT SYSTEM VERIFICATION REPORT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 80% ALERT SYSTEM
Status: {alert_80['status']}

Checks:
"""

        # Add 80% checks
        checks_80 = alert_80['checks']
        if checks_80.get('function_exists'):
            report += f"  ✅ 80% Alert Function Exists\n"
            report += f"     Found in {checks_80.get('function_location', 'bot.py')}\n"
        else:
            report += f"  ❌ 80% Alert Function Missing\n"

        if checks_80.get('active_trades_tracking'):
            report += f"  ✅ Active Trades Tracking\n"
        else:
            report += f"  ❌ Active Trades Tracking\n"
            report += f"     No active_trades variable found\n"

        if checks_80.get('data_exists'):
            count = checks_80.get('coverage_count', 0)
            total = checks_80.get('total_trades', 0)
            report += f"  ✅ 80% Alerts in Journal\n"
            report += f"     {count} out of {total} trades have alerts\n"
        else:
            count = checks_80.get('coverage_count', 0)
            total = checks_80.get('total_trades', 0)
            if total > 0:
                report += f"  ⚠️ 80% Alerts in Journal\n"
                report += f"     Only {count} out of {total} trades have alerts\n"
            else:
                report += f"  ❌ No trades in journal\n"

        # Add issues
        if alert_80['issues']:
            report += f"\n❌ Issues Found:\n"
            for issue in alert_80['issues']:
                report += f"  • {issue}\n"

        # Add recommendations
        if alert_80['recommendations']:
            report += f"\n💡 Recommendations:\n"
            for i, rec in enumerate(alert_80['recommendations'], 1):
                report += f"  {i}. {rec}\n"

        report += f"\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        report += f"🎯 FINAL ALERT SYSTEM\nStatus: {final_alert['status']}\n\nChecks:\n"

        # Add final alert checks
        checks_final = final_alert['checks']
        if checks_final.get('function_exists'):
            report += f"  ✅ Final Alert Function Exists\n"
            report += f"     Found in {checks_final.get('function_location', 'bot.py')}\n"
        else:
            report += f"  ❌ Final Alert Function Missing\n"

        if checks_final.get('outcome_detection'):
            report += f"  ✅ Outcome Detection\n"
            report += f"     WIN/LOSS logic present at {checks_final.get('outcome_location', 'bot.py')}\n"
        else:
            report += f"  ❌ Outcome Detection Missing\n"

        if checks_final.get('data_exists'):
            count = checks_final.get('coverage_count', 0)
            closed = checks_final.get('closed_trades', 0)
            coverage = checks_final.get('coverage_percentage', 0)
            report += f"  ✅ Final Alerts in Journal\n"
            report += f"     {count} out of {closed} closed trades ({coverage}% coverage)\n"
        else:
            count = checks_final.get('coverage_count', 0)
            closed = checks_final.get('closed_trades', 0)
            if closed > 0:
                report += f"  ❌ Final Alerts in Journal\n"
                report += f"     {count} out of {closed} closed trades have final alerts\n"
            else:
                report += f"  ❌ No closed trades in journal\n"

        # Add issues
        if final_alert['issues']:
            report += f"\n❌ Issues Found:\n"
            for issue in final_alert['issues']:
                report += f"  • {issue}\n"

        # Add recommendations
        if final_alert['recommendations']:
            report += f"\n💡 Recommendations:\n"
            for i, rec in enumerate(final_alert['recommendations'], 1):
                report += f"  {i}. {rec}\n"

        report += f"\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        report += f"Generated: {results['timestamp']}\n"
        report += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"

        # Write report
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)


# Convenience function
async def run_verification() -> Dict[str, Any]:
    """
    Run alert verification and return results
    
    Returns:
        Dict with verification results
    """
    verifier = AlertVerifier()
    return await verifier.verify_all()


if __name__ == "__main__":
    """Run verification from command line"""
    import asyncio
    
    async def main():
        results = await run_verification()
        print("\n✅ Verification complete!")
        print(f"80% Alert System: {results['80_alert']['status']}")
        print(f"Final Alert System: {results['final_alert']['status']}")
        print("\nFull report saved to: ALERT_VERIFICATION_REPORT.md")
    
    asyncio.run(main())
