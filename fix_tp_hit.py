#!/usr/bin/env python3
with open('bot.py', 'r') as f:
    lines = f.readlines()

# Намери handle_tp_hit функцията и добави update_trade_outcome
for i in range(len(lines)):
    # След close_position() затваряща скоба (около ред 12099)
    if i > 12095 and i < 12105 and '        )' in lines[i] and 'outcome=tp_level' in lines[i-1]:
        # Вмъкни update_trade_outcome СЛЕД затварящата скоба
        insert_code = '''
        # Update journal if journal_id exists
        if position.get("journal_id"):
            update_trade_outcome(
                trade_id=position["journal_id"],
                outcome="WIN",
                profit_loss_pct=pl_percent,
                notes=f"Auto-closed: {tp_level} hit at ${exit_price:,.2f}"
            )
'''
        lines.insert(i + 1, insert_code)
        break

with open('bot.py', 'w') as f:
    f.writelines(lines)

print("✅ fix_tp_hit.py applied!")
