from app import TTPProgram, ClientProgram, MerchantProgram
from squidasm.run.stack.config import StackNetworkConfig
from squidasm.run.stack.run import run

# Import network configuration from file
cfg = StackNetworkConfig.from_file("config.yaml")

# Initialize protocol programs
# Client credentials (shared secret established before protocol starts)
CLIENT_ID = "client_alice"
SECRET_TOKEN = "secret_token_abc123"
MERCHANT_ID = "merchant_shop_xyz"

ttp_program = TTPProgram()
client_program = ClientProgram(
    client_id=CLIENT_ID,
    secret_token=SECRET_TOKEN,
    merchant_id=MERCHANT_ID
)
merchant_program = MerchantProgram()

# Map each network node to its corresponding protocol program
programs = {
    "TTP": ttp_program,
    "Client": client_program,
    "Merchant": merchant_program
}

print("\n" + "="*60)
print("QUANTUM DIGITAL PAYMENT PROTOCOL SIMULATION")
print("="*60)
print("\nSetup:")
print(f"  Client ID: {CLIENT_ID}")
print(f"  Merchant ID: {MERCHANT_ID}")
print(f"  Security parameter λ: 8 qubits")
print("\nProtocol Steps:")
print("  1. TTP generates quantum token |P⟩ and sends to Client")
print("  2. Client measures token based on MAC(secret, merchant)")
print("  3. Client sends cryptogram to Merchant")
print("  4. Merchant forwards to TTP for verification")
print("  5. TTP verifies and accepts/rejects payment")
print("="*60)

# Run the simulation
results_list = run(
    config=cfg,
    programs=programs,
    num_times=1,
)

print("\n" + "="*60)
print("SIMULATION COMPLETE")
print("="*60)
print("\nResults:")

# Debug: Check the structure
print(f"\nType of results_list: {type(results_list)}")
print(f"Length: {len(results_list)}")
if results_list:
    print(f"Type of first element: {type(results_list[0])}")
    print(f"First element: {results_list[0]}")

# Handle the actual structure - results_list[0] is a list of (node_name, result) tuples
if results_list and len(results_list) > 0:
    for run_idx, run_results in enumerate(results_list):
        if run_idx > 0:
            print(f"\n--- Run {run_idx + 1} ---")
        
        # run_results is a list of tuples: [(node_name, result), ...]
        if isinstance(run_results, list):
            for item in run_results:
                if isinstance(item, tuple) and len(item) == 2:
                    node, result = item
                    print(f"\n{node}:")
                    if isinstance(result, dict):
                        for key, value in result.items():
                            if isinstance(value, str) and len(value) > 50:
                                print(f"  {key}: {value[:50]}...")
                            else:
                                print(f"  {key}: {value}")
                    else:
                        print(f"  {result}")

print("="*60)