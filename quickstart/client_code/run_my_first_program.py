import asyncio
import py_nillion_client as nillion
import os

from py_nillion_client import NodeKey, UserKey
from dotenv import load_dotenv
from nillion_python_helpers import get_quote_and_pay, create_nillion_client, create_payments_config

from cosmpy.aerial.client import LedgerClient
from cosmpy.aerial.wallet import LocalWallet
from cosmpy.crypto.keypairs import PrivateKey

def setup_environment():
    home = os.getenv("HOME")
    load_dotenv(f"{home}/.config/nillion/nillion-devnet.env")

async def main():
    setup_environment()

    cluster_id = os.getenv("NILLION_CLUSTER_ID")
    grpc_endpoint = os.getenv("NILLION_NILCHAIN_GRPC")
    chain_id = os.getenv("NILLION_NILCHAIN_CHAIN_ID")

    seed = "my_seed"
    userkey = UserKey.from_seed(seed)
    nodekey = NodeKey.from_seed(seed)
    client = create_nillion_client(userkey, nodekey)

    payments_config = create_payments_config(chain_id, grpc_endpoint)
    payments_client = LedgerClient(payments_config)
    payments_wallet = LocalWallet(
        PrivateKey(bytes.fromhex(os.getenv("NILLION_NILCHAIN_PRIVATE_KEY_0"))),
        prefix="nillion",
    )

    program_name = "main"
    program_mir_path = f"../nada_quickstart_programs/target/{program_name}.nada.bin"

    # Store program
    receipt_store_program = await get_quote_and_pay(
        client,
        nillion.Operation.store_program(program_mir_path),
        payments_wallet,
        payments_client,
        cluster_id,
    )
    action_id = await client.store_program(
        cluster_id, program_name, program_mir_path, receipt_store_program
    )
    print("Stored program. action_id:", action_id)

    # Define and store secrets with custom weights
    nr_parties = 5
    nr_criteria = 3
    secrets = {}

    # Custom weights for each party and criteria
    custom_weights = [
        [1, 2, 3],  # Weights for Party 0 for each criteria
        [2, 3, 4],  # Weights for Party 1 for each criteria
        [3, 4, 5],  # Weights for Party 2 for each criteria
        [4, 5, 6],  # Weights for Party 3 for each criteria
        [5, 6, 7],  # Weights for Party 4 for each criteria
    ]

    for p in range(nr_parties):
        for c in range(nr_criteria):
            feedback_key = f"p{p}_c{c}"
            role_key = f"role{p}_c{c}"
            weight_key = f"weight{p}_c{c}"
            secrets[feedback_key] = nillion.SecretUnsignedInteger(max(p * 10 + c * 5, 1))
            secrets[role_key] = nillion.SecretUnsignedInteger(custom_weights[p][c])
            secrets[weight_key] = nillion.SecretUnsignedInteger(custom_weights[p][c])
      
    new_secret = nillion.NadaValues(secrets)

    receipt_store = await get_quote_and_pay(
        client,
        nillion.Operation.store_values(new_secret, ttl_days=5),
        payments_wallet,
        payments_client,
        cluster_id,
    )

    # Set permissions for the stored values
    permissions = nillion.Permissions.default_for_user(client.user_id)
    permissions.add_compute_permissions({client.user_id: {f"{client.user_id}/{program_name}"}})

    store_id = await client.store_values(
        cluster_id, new_secret, permissions, receipt_store
    )
    print(f"Stored secrets. Store ID: {store_id}")

    # Setup compute
    compute_bindings = nillion.ProgramBindings(f"{client.user_id}/{program_name}")
    for p in range(nr_parties):
        compute_bindings.add_input_party(f"Party{p}", client.party_id)

    compute_bindings.add_output_party("OutParty", client.party_id)

    receipt_compute = await get_quote_and_pay(
        client,
        nillion.Operation.compute(f"{client.user_id}/{program_name}", nillion.NadaValues({})),
        payments_wallet,
        payments_client,
        cluster_id,
    )
    compute_id = await client.compute(
        cluster_id,
        compute_bindings,
        [store_id],
        nillion.NadaValues({}),
        receipt_compute
    )
    print(f"Computation initiated. Compute ID: {compute_id}")

    while True:
        compute_event = await client.next_compute_event()
        if isinstance(compute_event, nillion.ComputeFinishedEvent) and compute_event.uuid == compute_id:
            print(f"✅ Compute complete for compute_id {compute_event.uuid}")
            print(f"🖥️ The result is {compute_event.result.value}")
            return compute_event.result.value

if __name__ == "__main__":
    asyncio.run(main())
