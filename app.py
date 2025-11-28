import netsquid as ns
from squidasm.sim.stack.program import Program, ProgramContext, ProgramMeta
from netqasm.sdk.qubit import Qubit
import hashlib
import random

# Security parameter - length of quantum token
LAMBDA = 8

def mac(secret, message):
    """
    Message Authentication Code using SHA-256
    Returns a binary string of length LAMBDA
    """
    combined = f"{secret}{message}"
    hash_obj = hashlib.sha256(combined.encode())
    hash_bytes = hash_obj.digest()
    # Convert to binary string
    binary = ''.join(format(byte, '08b') for byte in hash_bytes)
    return binary[:LAMBDA]


class TTPProgram(Program):
    """Trusted Third Party (Bank) Program
    
    NOTE: In this simplified implementation, TTP sends classical information (b, B)
    instead of quantum states. The Client will prepare the quantum states locally
    based on this information for demonstration purposes. In a real quantum payment
    system, the TTP would send actual quantum states over a quantum channel.
    """
    NODE_NAME = "TTP"
    
    def __init__(self):
        super().__init__()
        # Database of clients and their secret tokens
        self.client_database = {
            "client_alice": "secret_token_abc123"
        }
        # Storage for quantum tokens
        self.token_storage = {}
    
    @property
    def meta(self) -> ProgramMeta:
        return ProgramMeta(
            name="ttp_program",
            csockets=["Client", "Merchant"],
            epr_sockets=[],
            max_qubits=1,
        )
    
    def run(self, context: ProgramContext):
        csocket_client = context.csockets["Client"]
        csocket_merchant = context.csockets["Merchant"]
        
        print(f"\n{ns.sim_time()} ns: TTP starting quantum payment protocol")
        print("=" * 60)
        
        # STEP 1: Generate random bitstring b and basis string B
        b = ''.join(str(random.randint(0, 1)) for _ in range(LAMBDA))
        B = ''.join(str(random.randint(0, 1)) for _ in range(LAMBDA))
        
        print(f"{ns.sim_time()} ns: TTP generated:")
        print(f"  b (bits):  {b}")
        print(f"  B (bases): {B}")
        print(f"  (0=computational |0⟩/|1⟩, 1=Hadamard |+⟩/|-⟩)")
        
        # Store token under client ID
        client_id = "client_alice"
        self.token_storage[client_id] = {"b": b, "B": B}
        
        # STEP 1: Display what quantum token |P⟩ would look like
        print(f"\n{ns.sim_time()} ns: TTP would prepare quantum token |P⟩:")
        token_description = []
        for j in range(LAMBDA):
            if B[j] == '0':  # Computational basis
                state = f"|{b[j]}⟩"
            else:  # Hadamard basis
                state = f"|{'+' if b[j]=='0' else '-'}⟩"
            token_description.append(state)
        print(f"  |P⟩ = {' '.join(token_description)}")
        
        # STEP 1: Send token information to Client
        # NOTE: In real implementation, these would be quantum states
        # For demonstration, we send classical description
        print(f"\n{ns.sim_time()} ns: TTP sending token to Client...")
        csocket_client.send({"b": b, "B": B})
        print(f"{ns.sim_time()} ns: TTP sent quantum token information")
        
        # STEP 4: Wait for verification request from Merchant
        print(f"\n{ns.sim_time()} ns: TTP waiting for verification request...")
        verification_msg = yield from csocket_merchant.recv()
        
        client_id = verification_msg["client_id"]
        kappa = verification_msg["kappa"]
        merchant_id = verification_msg["merchant_id"]
        
        print(f"\n{ns.sim_time()} ns: TTP received verification request:")
        print(f"  Client ID: {client_id}")
        print(f"  Merchant ID: {merchant_id}")
        print(f"  Cryptogram κ: {kappa}")
        
        # STEP 4: Verify the payment
        secret_token = self.client_database[client_id]
        stored_token = self.token_storage[client_id]
        b_original = stored_token["b"]
        B_original = stored_token["B"]
        
        # Calculate expected measurement basis
        m = mac(secret_token, merchant_id)
        print(f"\n{ns.sim_time()} ns: TTP verifying payment:")
        print(f"  Expected basis m: {m}")
        print(f"  Original basis B: {B_original}")
        print(f"  Original bits  b: {b_original}")
        print(f"  Received κ:       {kappa}")
        
        # Check: κ_j should equal b_j when m_j equals B_j
        matches = 0
        total_checked = 0
        verification_details = []
        
        for j in range(LAMBDA):
            if m[j] == B_original[j]:  # Matching basis
                total_checked += 1
                if kappa[j] == b_original[j]:
                    matches += 1
                    verification_details.append(f"✓ Pos {j}: match")
                else:
                    verification_details.append(f"✗ Pos {j}: MISMATCH!")
        
        print(f"\n{ns.sim_time()} ns: Verification details:")
        for detail in verification_details:
            print(f"  {detail}")
        
        # Accept if all matching positions are correct
        payment_accepted = (matches == total_checked and total_checked > 0)
        
        print(f"\n{ns.sim_time()} ns: TTP verification result:")
        print(f"  Positions with matching basis: {total_checked}/{LAMBDA}")
        print(f"  Correct measurements: {matches}/{total_checked}")
        print(f"  Payment status: {'✓ ACCEPTED' if payment_accepted else '✗ REJECTED'}")
        
        # Send result back to Merchant
        result = {"accepted": payment_accepted}
        csocket_merchant.send(result)
        
        print("=" * 60)
        return {"b": b, "B": B, "accepted": payment_accepted}


class ClientProgram(Program):
    """Client (Customer) Program
    
    NOTE: In this implementation, the Client receives classical information (b, B)
    from TTP and prepares quantum states locally, then measures them. This simulates
    the quantum protocol while working within SquidASM's constraints.
    """
    NODE_NAME = "Client"
    
    def __init__(self, client_id, secret_token, merchant_id):
        super().__init__()
        self.client_id = client_id
        self.secret_token = secret_token
        self.merchant_id = merchant_id
    
    @property
    def meta(self) -> ProgramMeta:
        return ProgramMeta(
            name="client_program",
            csockets=["TTP", "Merchant"],
            epr_sockets=[],
            max_qubits=LAMBDA,
        )
    
    def run(self, context: ProgramContext):
        csocket_ttp = context.csockets["TTP"]
        csocket_merchant = context.csockets["Merchant"]
        connection = context.connection
        
        print(f"\n{ns.sim_time()} ns: Client starting payment to {self.merchant_id}")
        
        # STEP 1: Receive quantum token information from TTP
        print(f"{ns.sim_time()} ns: Client receiving quantum token from TTP...")
        token_info = yield from csocket_ttp.recv()
        b = token_info["b"]
        B = token_info["B"]
        
        print(f"{ns.sim_time()} ns: Client received token information")
        print(f"  Token prepared with b={b}, B={B}")
        
        # Prepare qubits locally to simulate receiving quantum states
        print(f"\n{ns.sim_time()} ns: Client preparing quantum states locally...")
        qubits = []
        for j in range(LAMBDA):
            q = Qubit(connection)
            
            if B[j] == '0':  # Computational basis
                if b[j] == '1':
                    q.X()
            else:  # Hadamard basis
                q.H()
                if b[j] == '1':
                    q.Z()
            
            qubits.append(q)
        
        yield from connection.flush()
        print(f"{ns.sim_time()} ns: Client prepared {LAMBDA} qubits")
        
        # STEP 2: Calculate measurement basis m = MAC(C, M)
        m = mac(self.secret_token, self.merchant_id)
        print(f"\n{ns.sim_time()} ns: Client computed measurement basis:")
        print(f"  m = MAC(secret, merchant_id) = {m}")
        print(f"  (0=measure in computational, 1=measure in Hadamard)")
        
        # STEP 2: Measure qubits according to basis m
        print(f"\n{ns.sim_time()} ns: Client measuring qubits...")
        kappa = []
        
        for j in range(LAMBDA):
            q = qubits[j]
            
            if m[j] == '1':  # Measure in Hadamard basis
                q.H()  # Transform to computational basis for measurement
            
            # Measure in computational basis
            result = q.measure()
            kappa.append(result)
        
        yield from connection.flush()
        
        # Convert measurement results to string
        kappa_str = ''.join(str(k) for k in kappa)
        print(f"{ns.sim_time()} ns: Client measurement results (cryptogram):")
        print(f"  κ = {kappa_str}")
        
        # STEP 3: Send payment info to Merchant
        payment_data = {
            "client_id": self.client_id,
            "kappa": kappa_str
        }
        
        print(f"\n{ns.sim_time()} ns: Client sending payment to Merchant...")
        csocket_merchant.send(payment_data)
        
        return {"m": m, "kappa": kappa_str}


class MerchantProgram(Program):
    """Merchant (Store) Program"""
    NODE_NAME = "Merchant"
    MERCHANT_ID = "merchant_shop_xyz"
    
    @property
    def meta(self) -> ProgramMeta:
        return ProgramMeta(
            name="merchant_program",
            csockets=["Client", "TTP"],
            epr_sockets=[],
            max_qubits=1,
        )
    
    def run(self, context: ProgramContext):
        csocket_client = context.csockets["Client"]
        csocket_ttp = context.csockets["TTP"]
        
        print(f"\n{ns.sim_time()} ns: Merchant ready to receive payment")
        
        # STEP 3: Receive payment from Client
        payment_data = yield from csocket_client.recv()
        
        client_id = payment_data["client_id"]
        kappa = payment_data["kappa"]
        
        print(f"\n{ns.sim_time()} ns: Merchant received payment from {client_id}")
        print(f"  Cryptogram κ: {kappa}")
        
        # STEP 3: Forward to TTP for verification
        verification_request = {
            "client_id": client_id,
            "kappa": kappa,
            "merchant_id": self.MERCHANT_ID
        }
        
        print(f"\n{ns.sim_time()} ns: Merchant forwarding to TTP for verification...")
        csocket_ttp.send(verification_request)
        
        # Wait for TTP response
        result = yield from csocket_ttp.recv()
        
        if result["accepted"]:
            print(f"\n{ns.sim_time()} ns: Merchant: Payment ACCEPTED! ✓")
        else:
            print(f"\n{ns.sim_time()} ns: Merchant: Payment REJECTED! ✗")
        
        return {"accepted": result["accepted"]}