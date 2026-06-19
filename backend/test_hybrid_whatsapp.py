import asyncio
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')
sys.path.append(os.path.dirname(__file__))

import whatsapp_agent

async def main():
    print("=== TESTE DE ENVIO HÍBRIDO WHATSAPP ===")
    
    # Exibe canais ativos
    wpp_active = bool(whatsapp_agent.WPP_TOKEN)
    zapi_active = bool(whatsapp_agent.ZAPI_INSTANCE_ID and whatsapp_agent.ZAPI_TOKEN)
    
    print(f"Canal WPPConnect configurado: {wpp_active}")
    print(f"Canal Z-API configurado: {zapi_active}")
    
    # Destinatário de teste
    test_phone = "5585985902642" # Telefone do Diretor Eduardo
    test_message = "🌿 Olá Eduardo! Este é um teste do envio híbrido do atendimento LENA (WPPConnect + Z-API) atualizado e online. 🌿"
    
    print(f"\nSimulando envio de mensagem para {test_phone}...")
    await whatsapp_agent.send_whatsapp_message(test_phone, test_message)
    print("Simulação de envio concluída!")

if __name__ == "__main__":
    asyncio.run(main())
