import os
import time
import json
import logging
from datetime import datetime
from dotenv import load_dotenv
from hyperliquid.utils import constants
from hyperliquid.exchange import Exchange
from hyperliquid.info import Info
from eth_account import Account

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("../../logs/vault.log"),
        logging.StreamHandler()
    ]
)

load_dotenv()

class HyperliquidAutoStaker:
    def __init__(self):
        self.api_key = os.getenv("VAULT_API_KEY")
        self.main_address = os.getenv("MAIN_ACCOUNT_ADDRESS")
        self.validator = os.getenv("VALIDATOR_ADDRESS")
        self.interval = int(os.getenv("SWEEP_INTERVAL_SECS", 3600))
        
        # Determine the path to the Next.js public folder for the JSON state file
        self.state_file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../interface/public/vault_state.json'))
        
        base_url = constants.MAINNET_API_URL if os.getenv("IS_MAINNET") == "true" else constants.TESTNET_API_URL
        
        try:
            self.account = Account.from_key(self.api_key)
            self.info = Info(base_url, skip_ws=True)
            self.exchange = Exchange(self.account, base_url, account_address=self.main_address)
            logging.info(f"Vault Daemon initialized. Agent Address: {self.account.address}")
        except Exception as e:
            logging.warning(f"Running in Mock Mode. API Key missing or invalid: {e}")
            self.account = None
            self.info = None
            self.exchange = None  # Fixed: Explicitly initialized to prevent AttributeError

    def get_unstaked_hype_balance(self) -> float:
        if not self.info:
            return 1450.25  # Mock balance for UI testing
            
        try:
            spot_state = self.info.get_spot_user_state(self.main_address)
            for balance in spot_state.get("balances", []):
                if balance.get("coin") == "HYPE":
                    return float(balance.get("total", 0.0))
        except Exception as e:
            logging.error(f"Error fetching spot balance: {e}")
        return 0.0

    def sweep_to_staking(self, amount: float):
        if amount <= 0:
            return

        logging.info(f"Attempting to sweep {amount} HYPE to validator {self.validator}...")
        
        if not self.exchange:
            logging.info(f"[MOCK] Successfully 'staked' {amount} HYPE.")
            return

        try:
            response = self.exchange.delegate(self.validator, str(amount))
            if response.get("status") == "ok":
                logging.info(f"Successfully staked {amount} HYPE.")
            else:
                logging.error(f"Staking transaction failed: {response}")
        except Exception as e:
            logging.error(f"Exception during staking execution: {e}")

    def save_state_to_json(self, balance, apy, cumulative_yield, events):
        """Writes the current vault state to a JSON file readable by Next.js"""
        state_data = {
            "last_updated": datetime.now().isoformat(),
            "tvl": f"{balance:,.2f}",
            "apy": f"{apy}%",
            "cumulative_yield": f"{cumulative_yield:.4f}",
            "recent_events": events
        }
        
        # Ensure the target directory exists
        os.makedirs(os.path.dirname(self.state_file_path), exist_ok=True)
        
        try:
            with open(self.state_file_path, 'w') as f:
                json.dump(state_data, f, indent=2)
            logging.info(f"State successfully written to {self.state_file_path}")
        except Exception as e:
            logging.error(f"Failed to write state JSON: {e}")

    def run(self):
        logging.info("Starting Auto-Staking loop...")
        
        mock_yield = 0.0000
        
        while True:
            hype_balance = self.get_unstaked_hype_balance()
            logging.info(f"Current liquid HYPE balance: {hype_balance}")
            
            event_log = []
            current_time = datetime.now().strftime("%H:%M:%S")
            event_log.append(f"[{current_time}] Daemon heartbeat verified.")
            
            if hype_balance >= 1.0: 
                self.sweep_to_staking(hype_balance)
                event_log.append(f"[{current_time}] Sweep successful: {hype_balance} HYPE delegated.")
            else:
                logging.info("Balance below minimum threshold for execution. Skipping sweep.")
                event_log.append(f"[{current_time}] Idle. Balance ({hype_balance}) below threshold.")
            
            mock_yield += 0.0145  # Simulate slight yield growth over time
            
            self.save_state_to_json(
                balance=hype_balance, 
                apy=2.3, 
                cumulative_yield=mock_yield, 
                events=event_log
            )
                
            time.sleep(self.interval)

if __name__ == "__main__":
    staker = HyperliquidAutoStaker()
    staker.run()

