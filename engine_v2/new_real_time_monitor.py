# engine/signal_monitor.py

"""
Signal Monitor - PRODUCTION

STEP 15.2: Real-time Signal Monitoring

Responsibilities:
✔ Loads active signals
✔ Checks pending entry with live price + candle replay recovery
✔ Checks TP/SL with live price + multi-candle replay
✔ Handles ambiguous TP/SL same-candle cases without guessing sequence
✔ Integrates with SignalStorage
"""

import time
import os
import html
import requests
from typing import List, Optional, Dict
from datetime import datetime, timezone

from models.signal import Signal
from storage.signal_storage import SignalStorage


class RealTimePositionMonitor:
    """
    Signal Monitor - STEP 15.2

    Architecture:
    - LIVE LAYER:
        fast current-price checks for ENTRY / TP / SL
    - CANDLE RECONCILIATION LAYER:
        missed-touch recovery and lifecycle/statistics integrity
    """

    def __init__(
        self,
        bot=None,
        ict_80_handler=None,
        owner_chat_id=None,
        binance_price_url=None,
        binance_klines_url=None,
        storage=None,
        check_interval=60,
    ):
        self.bot = bot
        self.ict_80_handler = ict_80_handler
        self.owner_chat_id = owner_chat_id
        self.binance_price_url = binance_price_url
        self.binance_klines_url = binance_klines_url

        self.storage = storage or SignalStorage()

        # Isolated experimental lifecycle storage.
        self.shadow_storage = SignalStorage(
            base_path="data/shadow_signals"
        )

        self.send_lifecycle_notifications = True

        self.check_interval = check_interval
        self.is_running = False

        self.pending_expiry_candles = 2
        self.replay_candle_limit = 10
      
    def __init__(
        self,
        bot,
        ict_80_handler,
        owner_chat_id,
        binance_price_url,
        binance_klines_url
    ):
        self.storage = storage or SignalStorage()

        # Isolated experimental lifecycle storage.
        # Production storage and behavior remain unchanged.
        self.shadow_storage = SignalStorage(
            base_path="data/shadow_signals"
        )

        # Telegram remains enabled for the normal Production pass.
        self.send_lifecycle_notifications = True
        
        self.check_interval = check_interval
        self.is_running = False

        # If entry is not triggered within N candles after signal creation,
        # the setup expires without being counted as win/loss.
        self.pending_expiry_candles = 2

        # Replay safety buffer. We usually need only a few candles, but 10 gives
        # enough room for missed scheduler runs, restart delays, and API lag.
        self.replay_candle_limit = 10

    # =========================================================
    # MAIN MONITORING
    # =========================================================

    def start_monitoring(self):
        """
        Starts continuous monitoring loop.

        Note:
        In production main.py uses scheduler.check_all_signals_once().
        This loop is kept for standalone/manual monitor usage.
        """
        self.is_running = True
        print("🟢 Signal Monitor started")

        while self.is_running:
            try:
                self._check_all_signals()
                time.sleep(self.check_interval)

            except KeyboardInterrupt:
                print("\n🔴 Signal Monitor stopped by user")
                self.is_running = False
                break

            except Exception as e:
                print(f"❌ Error in monitoring loop: {e}")
                time.sleep(self.check_interval)

    def stop_monitoring(self):
        """Stops monitoring loop."""
        self.is_running = False
        print("🔴 Signal Monitor stopped")

    def _run_shadow_pass(self, callback):
        """
        Run the existing lifecycle logic against Shadow Storage.

        Production state is restored unconditionally, including after errors.
        A Shadow failure must never interrupt Production monitoring.
        """
        production_storage = self.storage
        production_notifications = (
            self.send_lifecycle_notifications
        )

        try:
            self.storage = self.shadow_storage
            self.send_lifecycle_notifications = False
            return callback()

        except Exception as e:
            print(
                f"⚠️ Shadow lifecycle pass failed: "
                f"{type(e).__name__}: {e}"
            )
            return None

        finally:
            self.storage = production_storage
            self.send_lifecycle_notifications = (
                production_notifications
            )

    # =========================================================
    # CHECK SIGNALS
    # =========================================================

    def _check_all_signals_live_current_storage(self):
        """
        Fast LIVE monitoring pass.

        Uses one live price fetch per symbol per pass:
        - pending entry activation
        - entered TP/SL detection

        Important:
        - Live price is symbol-based, not timeframe-based.
        - The same BTCUSDT live price is valid for BTCUSDT 15M, 30M, 1H, 4H signals.
        - Each signal still uses its own entry / SL / TP levels.
        """
        active_signals = self.storage.load_active_signals()

        if not active_signals:
            return

        symbols = []
        for signal in active_signals:
            symbol = getattr(signal, "symbol", None)
            if symbol:
                symbols.append(symbol)

        prices_by_symbol = self._fetch_current_prices(symbols)

        for signal in active_signals:
            symbol = getattr(signal, "symbol", None)
            if not symbol:
                continue

            live_price = prices_by_symbol.get(symbol)

            # If price is unavailable, skip this signal for this pass.
            # Do not call check_signal_live without price, because that would
            # trigger another individual HTTP request and defeat the cache.
            if live_price is None:
                continue

            self.check_signal_live(signal, current_price=live_price)

    def check_all_signals_live_once(self):
        """
        Run one LIVE monitoring pass:

        1. Production storage
        2. Shadow storage, isolated and without Telegram notifications
        """
        # Production first — existing behavior remains unchanged.
        self._check_all_signals_live_current_storage()

        # Shadow second — isolated from Production.
        self._run_shadow_pass(
            self._check_all_signals_live_current_storage
        )
            
    def check_all_signals_once(self):
        """
        Public one-shot full monitoring check.

        Backward-compatible:
        - runs LIVE first
        - then REPLAY if needed
        """
        self._check_all_signals()

    def _check_all_signals(self):
        """
        Full lifecycle monitoring cycle:

        1. Complete Production lifecycle
        2. Complete Shadow lifecycle
        """
        # Production — original full cycle and original order.
        self._check_all_signals_current_storage()

        # Shadow — same full lifecycle logic, isolated and without Telegram.
        self._run_shadow_pass(
            self._check_all_signals_current_storage
        )
        
    def _check_all_signals_replay_current_storage(self):
        """
        Slow REPLAY monitoring pass.

        Uses recent closed candles:
        - missed pending entry recovery
        - missed TP/SL recovery
        - ambiguous TP/SL same-candle detection
        - pending expiry after replay check
        """
        active_signals = self.storage.load_active_signals()

        if not active_signals:
            return

        # print(f"🧾 REPLAY checking {len(active_signals)} active signal(s)...")

        for signal in active_signals:
            self.check_signal_replay(signal)

    def _check_all_signals_current_storage(self):
        """
        Run the complete lifecycle cycle against self.storage:
        LIVE first, then REPLAY.
        """
        self._check_all_signals_live_current_storage()
        self._check_all_signals_replay_current_storage()

    def check_all_signals_replay_once(self):
        """
        Run one REPLAY monitoring pass:

        1. Production storage
        2. Shadow storage, isolated and without Telegram notifications
        """
        # Production first — existing behavior remains unchanged.
        self._check_all_signals_replay_current_storage()

        # Shadow second — isolated from Production.
        self._run_shadow_pass(
            self._check_all_signals_replay_current_storage
        )
    def check_signal_live(
        self,
        signal: Signal,
        current_price: Optional[float] = None
    ) -> Optional[str]:
        """
        LIVE layer check.

        Fast current-price only:
        - pending -> entered
        - entered -> win/loss

        No candle fetching.
        No replay.
        No expiry.
        """
        live_price = current_price

        if live_price is None:
            live_price = self._fetch_current_price(signal.symbol)

        if live_price is None:
            print(f"⚠️ LIVE price unavailable for {signal.symbol}")
            return None

        live_price = float(live_price)

        # Quiet normal LIVE checks.
        # Only lifecycle events are printed: entry, TP, SL.

        # Pending -> entered
        if not signal.entered:
            entry_hit = self._pending_entry_hit(signal, live_price)

            if entry_hit:
                signal.mark_as_entered(
                    trigger_price=signal.entry,
                    timestamp=datetime.utcnow().isoformat() + "Z"
                )

                self.storage.update_signal(signal)

                print(
                    f"🟡 ENTRY TRIGGERED LIVE: {signal.symbol} {signal.timeframe} | "
                    f"direction={signal.direction} | "
                    f"entry={signal.entry} | "
                    f"live_price={live_price}"
                )

                self._send_telegram_lifecycle_message(
                    self._format_entry_confirmed_message(signal, live_price)
                )

                return "entered"

            return None

        # Entered -> live TP/SL
        live_exit = self._live_exit_hit(signal, live_price)

        if live_exit:
            result = live_exit["result"]
            close_price = live_exit["price"]
            close_reason = live_exit["reason"]

            print(
                f"{'🟢' if result == 'win' else '🔴'} LIVE EXIT HIT: "
                f"{signal.symbol} {signal.timeframe} | "
                f"result={result} | reason={close_reason} | price={close_price}"
            )

            self._close_signal(
                signal,
                result,
                close_price,
                close_reason
            )

            return result

        return None

    def check_signal_replay(
        self,
        signal: Signal
    ) -> Optional[str]:
        """
        REPLAY layer check.

        Uses recent closed candles:
        - missed entry recovery
        - missed TP/SL recovery
        - ambiguous same-candle TP/SL detection
        - pending expiry after recovery check
        """
        recent_candles = self._fetch_recent_closed_candles(
            signal.symbol,
            signal.timeframe,
            limit=self.replay_candle_limit
        )

        if not recent_candles:
            print(f"⚠️ REPLAY candles unavailable for {signal.symbol} {signal.timeframe}")
            return None

        latest_candle = recent_candles[-1]
        latest_close_time = latest_candle.get("close_time")

        # print(
        #     f"🧾 REPLAY Monitoring {signal.symbol} {signal.timeframe} | "
        #     f"entry={signal.entry} sl={signal.stop_loss} tp={signal.take_profit} | "
        #     f"status={signal.status} entered={signal.entered} | "
        #     f"latest_close_time={latest_close_time}"
        # )

        # Pending -> candle entry recovery
        if not signal.entered:
            entry_recovery_candle = self._recover_pending_entry_from_candles(
                signal,
                recent_candles
            )

            if entry_recovery_candle:
                recovered_at = (
                    entry_recovery_candle.get("close_time")
                    or datetime.utcnow().isoformat() + "Z"
                )

                signal.mark_as_entered(
                    trigger_price=signal.entry,
                    timestamp=recovered_at
                )

                signal.last_candle_close_time = recovered_at
                self.storage.update_signal(signal)

                print(
                    f"🟡 ENTRY RECOVERED FROM CANDLE: {signal.symbol} {signal.timeframe} | "
                    f"direction={signal.direction} | entry={signal.entry} | "
                    f"candle_close_time={recovered_at}"
                )

                self._send_telegram_lifecycle_message(
                    self._format_entry_confirmed_message(signal, float(signal.entry))
                )

                return "entered"

            # Expire only after replay confirms entry was not touched.
            if self._is_pending_signal_expired(signal):
                self._expire_pending_signal(signal)
                return "expired"

            return None

        # Entered -> candle replay TP/SL
        replay_exit = self._replay_exit_from_candles(signal, recent_candles)

        if replay_exit:
            result = replay_exit["result"]
            close_price = replay_exit["price"]
            close_reason = replay_exit["reason"]

            if result == "ambiguous":
                print(
                    f"🟠 AMBIGUOUS EXIT: {signal.symbol} {signal.timeframe} | "
                    f"entry={signal.entry} sl={signal.stop_loss} tp={signal.take_profit} | "
                    f"candle_close_time={replay_exit.get('candle_close_time')}"
                )
            else:
                print(
                    f"{'🟢' if result == 'win' else '🔴'} CANDLE REPLAY EXIT HIT: "
                    f"{signal.symbol} {signal.timeframe} | "
                    f"result={result} | reason={close_reason} | price={close_price}"
                )

            self._close_signal(
                signal,
                result,
                close_price,
                close_reason
            )

            return result

        # No replay exit. Update last processed candle only for entered signals.
        signal.last_candle_close_time = latest_close_time
        self.storage.update_signal(signal)

        return None

    def check_signal(
        self,
        signal: Signal,
        current_price: Optional[float] = None
    ) -> Optional[str]:
        """
        Backward-compatible full check.

        Runs LIVE first, then REPLAY only if LIVE did not close/enter the signal.
        Production scheduler should use:
        - check_signal_live()
        - check_signal_replay()
        separately.
        """
        live_result = self.check_signal_live(signal, current_price=current_price)

        if live_result in ("entered", "win", "loss", "ambiguous", "expired"):
            return live_result

        refreshed = self.storage.load_signal(signal.signal_id) or signal

        replay_result = self.check_signal_replay(refreshed)
        return replay_result

    # =========================================================
    # CLOSE SIGNAL
    # =========================================================

    def _close_signal(
        self,
        signal: Signal,
        result: str,
        close_price: float,
        close_reason: str
    ):
        """
        Closes signal and moves it to closed/.

        result:
        - "win"
        - "loss"
        - "ambiguous"

        Important:
        SignalStorage.move_to_closed must preserve non-win/loss results.
        If storage currently only expects win/loss, update storage next.
        """
        success = self.storage.move_to_closed(
            signal,
            result,
            close_price,
            close_reason
        )

        if success:
            if signal.direction == "bullish":
                pnl = close_price - signal.entry
            else:
                pnl = signal.entry - close_price

            pnl_pct = (pnl / signal.entry) * 100 if signal.entry else 0.0

            if result == "win":
                result_emoji = "🟢"
            elif result == "loss":
                result_emoji = "🔴"
            else:
                result_emoji = "🟠"

            print(f"{result_emoji} Signal closed: {signal.symbol}")
            print(f"   Result: {result}")
            print(f"   Entry: {signal.entry}")
            print(f"   Close: {close_price}")
            print(f"   P&L: {pnl_pct:.2f}%")
            print(f"   RR: {signal.rr:.2f}")

            self._send_telegram_lifecycle_message(
                self._format_closed_message(
                    signal=signal,
                    result=result,
                    close_price=close_price,
                    close_reason=close_reason
                )
            )

    # =========================================================
    # TELEGRAM LIFECYCLE NOTIFICATIONS
    # =========================================================

    def _send_telegram_lifecycle_message(
        self,
        message: str
    ) -> bool:
        """
        Send lifecycle notification to Telegram.

        Used for:
        - ENTRY CONFIRMED
        - PENDING EXPIRED
        - TP/SL/AMBIGUOUS RESULT
        """

        if not self.send_lifecycle_notifications:
            return False
            
        try:
            token = os.getenv("TELEGRAM_BOT_TOKEN")
            chat_id = os.getenv("TELEGRAM_CHAT_ID")

            if not token or not chat_id:
                print("⚠️ Telegram lifecycle notification skipped: missing credentials")
                return False

            response = requests.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                data={
                    "chat_id": chat_id,
                    "text": message,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": True,
                },
                timeout=10
            )
            response.raise_for_status()
            return True

        except Exception as e:
            print(f"❌ Telegram lifecycle notification failed: {e}")
            return False

    def _format_entry_confirmed_message(
        self,
        signal: Signal,
        live_price: float
    ) -> str:
        direction_text = "LONG 📈" if signal.direction == "bullish" else "SHORT 📉"

        return (
            "🟢 <b>ENTRY CONFIRMED / ACTIVE</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"<b>{html.escape(signal.symbol)}</b> - {direction_text}\n"
            f"⏰ Timeframe: <b>{html.escape(signal.timeframe)}</b>\n"
            f"🆔 ID: <code>{html.escape(signal.signal_id)}</code>\n\n"
            f"🎯 Entry: <code>{float(signal.entry):.4f}</code>\n"
            f"📍 Trigger price: <code>{float(live_price):.4f}</code>\n"
            f"🛑 Stop Loss: <code>{float(signal.stop_loss):.4f}</code>\n"
            f"💰 TP1: <code>{float(signal.take_profit):.4f}</code>\n"
            f"⚖️ RR: <b>{float(signal.rr):.2f}</b>\n\n"
            "✅ Сигналът вече е entered и се следи за TP/SL."
        )

    def _format_expired_message(
        self,
        signal: Signal
    ) -> str:
        direction_text = "LONG 📈" if signal.direction == "bullish" else "SHORT 📉"

        return (
            "⏳ <b>PENDING ENTRY EXPIRED</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"<b>{html.escape(signal.symbol)}</b> - {direction_text}\n"
            f"⏰ Timeframe: <b>{html.escape(signal.timeframe)}</b>\n"
            f"🆔 ID: <code>{html.escape(signal.signal_id)}</code>\n\n"
            f"🎯 Entry: <code>{float(signal.entry):.4f}</code>\n"
            f"🛑 Stop Loss: <code>{float(signal.stop_loss):.4f}</code>\n"
            f"💰 TP1: <code>{float(signal.take_profit):.4f}</code>\n\n"
            f"⚠️ Entry не беше достигнато в рамките на "
            f"{self.pending_expiry_candles} candles.\n"
            "Сигналът е премахнат от active и НЕ се брои като загуба."
        )

    def _format_closed_message(
        self,
        signal: Signal,
        result: str,
        close_price: float,
        close_reason: str
    ) -> str:
        direction_text = "LONG 📈" if signal.direction == "bullish" else "SHORT 📉"

        metadata = getattr(signal, "metadata", None)
        if not isinstance(metadata, dict):
            metadata = {}

        setup_mode = (
            metadata.get("strategy_mode")
            or metadata.get("setup_mode")
            or getattr(signal, "strategy_mode", None)
            or getattr(signal, "setup_mode", None)
            or "anchor_retest"
        )

        if setup_mode == "anchor_retest":
            setup_mode_label = "Mode 1 — Anchor Retest"
        elif setup_mode in ["anchored_reclaim_continuation", "ob_origin_rejection"]:
            setup_mode_label = "Mode 2 — Anchored Reclaim Continuation"
        else:
            setup_mode_label = str(setup_mode).replace("_", " ").title()

        if result == "win":
            title = "🟢 <b>TP HIT / WIN</b>"
        elif result == "loss":
            title = "🔴 <b>SL HIT / LOSS</b>"
        else:
            title = "🟠 <b>TP/SL AMBIGUOUS</b>"

        if signal.direction == "bullish":
            pnl = close_price - signal.entry
        else:
            pnl = signal.entry - close_price

        pnl_pct = (pnl / signal.entry) * 100 if signal.entry else 0.0

        extra = ""
        if result == "ambiguous":
            extra = (
                "\n\n⚠️ В една и съща candle са достигнати и TP, и SL.\n"
                "Редът на ударите не може да бъде доказан от OHLC данните, "
                "затова резултатът се пази като AMBIGUOUS, без да се брои като win/loss."
            )

        return (
            f"{title}\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"<b>{html.escape(signal.symbol)}</b> - {direction_text}\n"
            f"⏰ Timeframe: <b>{html.escape(signal.timeframe)}</b>\n"
            f"🧠 Режим: <b>{html.escape(setup_mode_label)}</b>\n"
            f"🆔 ID: <code>{html.escape(signal.signal_id)}</code>\n\n"
            f"🎯 Entry: <code>{float(signal.entry):.4f}</code>\n"
            f"📍 Close: <code>{float(close_price):.4f}</code>\n"
            f"🧾 Reason: <b>{html.escape(close_reason)}</b>\n\n"
            f"📊 P&L: <b>{pnl_pct:.2f}%</b>\n"
            f"⚖️ RR: <b>{float(signal.rr):.2f}</b>"
            f"{extra}"
        )

    # =========================================================
    # CANDLE REPLAY HELPERS
    # =========================================================

    def _parse_candle_time_utc(self, value) -> Optional[datetime]:
        """
        Parse candle close_time safely as UTC datetime.
        """
        return self._parse_signal_timestamp_utc(value)

    def _filter_candles_after_time(
        self,
        candles: List[Dict],
        after_time
    ) -> List[Dict]:
        """
        Return only candles with close_time after given UTC datetime/string.
        """
        after_dt = self._parse_signal_timestamp_utc(after_time)

        if after_dt is None:
            return candles

        filtered = []

        for candle in candles:
            candle_dt = self._parse_candle_time_utc(candle.get("close_time"))
            if candle_dt is None:
                continue

            if candle_dt > after_dt:
                filtered.append(candle)

        return filtered

    def _entry_trigger_model(
        self,
        signal: Signal
    ) -> str:
        """
        Read entry trigger model from signal metadata.

        New Mode 1:
        - reaction_breakout

        Legacy:
        - empty / missing metadata -> old anchor limit behavior
        """
        metadata = getattr(signal, "metadata", None)
        if not isinstance(metadata, dict):
            metadata = {}

        return str(metadata.get("entry_trigger_model") or "").strip().lower()

    def _is_reaction_breakout_entry(
        self,
        signal: Signal
    ) -> bool:
        """
        True for new reaction-candle breakout entries.
        """
        trigger_model = self._entry_trigger_model(signal)
        entry_type = str(getattr(signal, "entry_type", "") or "").strip().lower()

        return (
            trigger_model in [
                "reaction_breakout",
                "reaction_break",
                "reaction_candle_breakout",
            ]
            or entry_type == "reaction_break"
        )

    def _pending_entry_hit(
        self,
        signal: Signal,
        live_price: float
    ) -> bool:
        """
        Pending entry trigger logic.

        New reaction_breakout:
        - bullish: live_price >= entry
        - bearish: live_price <= entry

        Legacy anchor/limit:
        - bullish: live_price <= entry
        - bearish: live_price >= entry
        """
        live_price = float(live_price)
        entry = float(signal.entry)

        if self._is_reaction_breakout_entry(signal):
            if signal.direction == "bullish":
                return live_price >= entry

            if signal.direction == "bearish":
                return live_price <= entry

            return False

        # Legacy behavior for old active signals.
        if signal.direction == "bullish":
            return live_price <= entry

        if signal.direction == "bearish":
            return live_price >= entry

        return False

    def _entry_hit_in_candle(
        self,
        signal: Signal,
        candle: Dict
    ) -> bool:
        """
        Check if pending entry was triggered inside a closed candle.

        Backward-compatible:
        - legacy anchor/limit entries use old touch logic
        - reaction_breakout entries use breakout trigger logic
        """
        high = float(candle["high"])
        low = float(candle["low"])
        entry = float(signal.entry)

        if self._is_reaction_breakout_entry(signal):
            if signal.direction == "bullish":
                return high >= entry

            if signal.direction == "bearish":
                return low <= entry

            return False

        # Legacy anchor-edge / limit-style behavior.
        if signal.direction == "bullish":
            return low <= entry

        if signal.direction == "bearish":
            return high >= entry

        return False

    def _recover_pending_entry_from_candles(
        self,
        signal: Signal,
        candles: List[Dict]
    ) -> Optional[Dict]:
        """
        Recover missed pending entry touch from closed candles.

        Returns candle dict if entry was touched.
        """
        if not candles:
            return None

        start_time = signal.last_candle_close_time or signal.timestamp
        replay_candles = self._filter_candles_after_time(candles, start_time)

        for candle in replay_candles:
            if self._entry_hit_in_candle(signal, candle):
                return candle

        return None

    def _live_exit_hit(
        self,
        signal: Signal,
        live_price: float
    ) -> Optional[Dict]:
        """
        Detect live TP/SL hit from current price.

        Returns:
            {"result": "win"|"loss", "price": float, "reason": str}
            or None
        """
        live_price = float(live_price)

        if signal.direction == "bullish":
            if live_price <= float(signal.stop_loss):
                return {
                    "result": "loss",
                    "price": float(signal.stop_loss),
                    "reason": "live_sl_hit"
                }

            if live_price >= float(signal.take_profit):
                return {
                    "result": "win",
                    "price": float(signal.take_profit),
                    "reason": "live_tp_hit"
                }

        elif signal.direction == "bearish":
            if live_price >= float(signal.stop_loss):
                return {
                    "result": "loss",
                    "price": float(signal.stop_loss),
                    "reason": "live_sl_hit"
                }

            if live_price <= float(signal.take_profit):
                return {
                    "result": "win",
                    "price": float(signal.take_profit),
                    "reason": "live_tp_hit"
                }

        return None

    def _exit_hit_in_candle(
        self,
        signal: Signal,
        candle: Dict
    ) -> Optional[Dict]:
        """
        Detect TP/SL hit inside one closed candle.

        If both TP and SL are hit in the same candle:
        result = ambiguous
        """
        high = float(candle["high"])
        low = float(candle["low"])

        tp = float(signal.take_profit)
        sl = float(signal.stop_loss)

        if signal.direction == "bullish":
            tp_hit = high >= tp
            sl_hit = low <= sl

        elif signal.direction == "bearish":
            tp_hit = low <= tp
            sl_hit = high >= sl

        else:
            return None

        if tp_hit and sl_hit:
            return {
                "result": "ambiguous",
                "price": float(signal.entry),
                "reason": "tp_sl_same_candle",
                "candle_close_time": candle.get("close_time")
            }

        if tp_hit:
            return {
                "result": "win",
                "price": tp,
                "reason": "candle_replay_tp_hit",
                "candle_close_time": candle.get("close_time")
            }

        if sl_hit:
            return {
                "result": "loss",
                "price": sl,
                "reason": "candle_replay_sl_hit",
                "candle_close_time": candle.get("close_time")
            }

        return None

    def _replay_exit_from_candles(
        self,
        signal: Signal,
        candles: List[Dict]
    ) -> Optional[Dict]:
        """
        Replay TP/SL checks across closed candles since last processed candle.
        """
        if not candles:
            return None

        start_time = (
            signal.last_candle_close_time
            or getattr(signal, "entered_at", None)
            or signal.timestamp
        )

        replay_candles = self._filter_candles_after_time(candles, start_time)

        for candle in replay_candles:
            exit_hit = self._exit_hit_in_candle(signal, candle)
            if exit_hit:
                return exit_hit

        return None

    # =========================================================
    # PENDING ENTRY EXPIRY
    # =========================================================

    def _timeframe_minutes(self, timeframe: str) -> int:
        """
        Convert timeframe to minutes.
        Used for pending-entry expiry.
        """
        tf_map = {
            "15M": 15,
            "30M": 30,
            "1H": 60,
            "2H": 120,
            "4H": 240,
            "1D": 1440,
        }
        return tf_map.get(str(timeframe).upper(), 15)

    def _parse_signal_timestamp_utc(self, value) -> Optional[datetime]:
        """
        Parse signal timestamp safely as UTC datetime.
        """
        if not value:
            return None

        try:
            dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))

            if dt.tzinfo is None:
                return dt.replace(tzinfo=timezone.utc)

            return dt.astimezone(timezone.utc)

        except Exception:
            return None

    def _is_pending_signal_expired(self, signal: Signal) -> bool:
        """
        Pending/active signal expires if entry was not triggered
        within N candles after signal creation.

        Important:
        - Applies only before entry.
        - Does NOT close as loss.
        - Deletes from active storage only.
        """
        if signal.entered:
            return False

        created_at = self._parse_signal_timestamp_utc(signal.timestamp)

        if not created_at:
            return False

        tf_minutes = self._timeframe_minutes(signal.timeframe)
        max_age_minutes = tf_minutes * self.pending_expiry_candles

        age_minutes = (
            datetime.now(timezone.utc) - created_at
        ).total_seconds() / 60

        return age_minutes > max_age_minutes

    def _expire_pending_signal(self, signal: Signal) -> bool:
        """
        Remove pending signal from active storage without counting it
        as win or loss.
        """
        print(
            f"⏳ Pending signal expired before entry: "
            f"{signal.symbol} {signal.timeframe} {signal.direction} | "
            f"signal_id={signal.signal_id} | "
            f"entry={signal.entry} | "
            f"created_at={signal.timestamp} | "
            f"expiry_candles={self.pending_expiry_candles}"
        )

        self._send_telegram_lifecycle_message(
            self._format_expired_message(signal)
        )

        return self.storage.delete_signal(signal.signal_id)

    # =========================================================
    # PRICE FETCHING
    # =========================================================

    def _fetch_last_closed_candle(self, symbol: str, timeframe: str) -> Optional[Dict]:
        """
        Fetch last CLOSED candle from Binance klines API for the signal timeframe.
        """
        try:
            interval_map = {
                "15M": "15m",
                "30M": "30m",
                "1H": "1h",
                "2H": "2h",
                "4H": "4h",
                "1D": "1d",
            }

            interval = interval_map.get(str(timeframe).upper())
            if not interval:
                print(f"⚠️ Unsupported timeframe for monitoring: {timeframe}")
                return None

            response = requests.get(
                "https://api.binance.com/api/v3/klines",
                params={
                    "symbol": symbol,
                    "interval": interval,
                    "limit": 2
                },
                timeout=10
            )
            response.raise_for_status()

            data = response.json()
            if not data or len(data) < 2:
                return None

            candle = data[-2]

            return {
                "open": float(candle[1]),
                "high": float(candle[2]),
                "low": float(candle[3]),
                "close": float(candle[4]),
                "close_time": datetime.utcfromtimestamp(candle[6] / 1000).isoformat() + "Z",
            }

        except Exception as e:
            print(f"❌ Error fetching candle for {symbol} {timeframe}: {e}")
            return None

    def _fetch_recent_closed_candles(
        self,
        symbol: str,
        timeframe: str,
        limit: int = 10
    ) -> List[Dict]:
        """
        Fetch recent CLOSED candles from Binance klines API.

        Used for candle-window recovery:
        - missed entry touch
        - missed TP/SL
        - lifecycle reconciliation
        """
        try:
            interval_map = {
                "15M": "15m",
                "30M": "30m",
                "1H": "1h",
                "2H": "2h",
                "4H": "4h",
                "1D": "1d",
            }

            interval = interval_map.get(str(timeframe).upper())
            if not interval:
                print(f"⚠️ Unsupported timeframe for replay: {timeframe}")
                return []

            response = requests.get(
                "https://api.binance.com/api/v3/klines",
                params={
                    "symbol": symbol,
                    "interval": interval,
                    "limit": max(3, int(limit) + 1)
                },
                timeout=10
            )
            response.raise_for_status()

            data = response.json()
            if not data or len(data) < 2:
                return []

            # Exclude current still-open candle.
            closed = data[:-1]

            candles = []
            for candle in closed:
                candles.append({
                    "open": float(candle[1]),
                    "high": float(candle[2]),
                    "low": float(candle[3]),
                    "close": float(candle[4]),
                    "close_time": datetime.utcfromtimestamp(candle[6] / 1000).isoformat() + "Z",
                })

            return candles

        except Exception as e:
            print(f"❌ Error fetching recent candles for {symbol} {timeframe}: {e}")
            return []

    def _fetch_current_prices(self, symbols):
        """
        Fetch current market prices for multiple symbols in one Binance request.

        This prevents repeated HTTP calls when several active signals use
        the same symbol across different timeframes.
        """
        unique_symbols = sorted({
            str(symbol).upper()
            for symbol in symbols
            if symbol
        })

        if not unique_symbols:
            return {}

        try:
            import json

            response = requests.get(
                "https://api.binance.com/api/v3/ticker/price",
                params={"symbols": json.dumps(unique_symbols, separators=(",", ":"))},
                timeout=5
            )
            response.raise_for_status()

            data = response.json()
            prices = {}

            for item in data:
                symbol = item.get("symbol")
                price = item.get("price")

                if symbol in unique_symbols and price is not None:
                    prices[symbol] = float(price)

            return prices

        except Exception as e:
            print(f"❌ Error fetching batch prices: {e}")

            # Safe fallback: if batch request fails, use old one-by-one method.
            prices = {}

            for symbol in unique_symbols:
                price = self._fetch_current_price(symbol)
                if price is not None:
                    prices[symbol] = price

            return prices

    def _fetch_current_price(self, symbol: str) -> Optional[float]:
        """
        Fetch current market price from Binance.
        """
        try:
            response = requests.get(
                "https://api.binance.com/api/v3/ticker/price",
                params={"symbol": symbol},
                timeout=10
            )
            response.raise_for_status()

            data = response.json()
            return float(data["price"])

        except Exception as e:
            print(f"❌ Error fetching price for {symbol}: {e}")
            return None

    def _mock_price(self, symbol: str) -> float:
        """
        Mock price for testing.
        """
        mock_prices = {
            "BTCUSDT": 84500.0,
            "ETHUSDT": 3200.0,
            "SOLUSDT": 140.0
        }
        return mock_prices.get(symbol, 50000.0)

    # =========================================================
    # STATISTICS
    # =========================================================

    def get_active_signals_summary(self) -> Dict:
        """
        Returns active signals summary.
        """
        active_signals = self.storage.load_active_signals()

        summary = {
            "total_active": len(active_signals),
            "signals": []
        }

        for signal in active_signals:
            summary["signals"].append({
                "symbol": signal.symbol,
                "direction": signal.direction,
                "entry": signal.entry,
                "sl": signal.stop_loss,
                "tp": signal.take_profit,
                "rr": signal.rr
            })

        return summary


# ============================================================
# HELPER
# ============================================================

def monitor_signals(check_interval: int = 60):
    """
    Helper function - Start monitoring.

    Usage:
        from engine.signal_monitor import monitor_signals
        monitor_signals(check_interval=60)
    """
    monitor = RealTimePositionMonitor(check_interval=check_interval)
    monitor.start_monitoring()
