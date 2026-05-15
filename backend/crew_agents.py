from crewai import Agent, Task, Crew, Process
from anthropic import Anthropic
import os

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

SONNET = "claude-sonnet-4-6"
OPUS   = "claude-opus-4-6"
HAIKU  = "claude-haiku-4-5-20251001"

def make_agent(name, role, goal, backstory, model=SONNET):
    return Agent(
        role=f"{name} — {role}",
        goal=goal,
        backstory=backstory,
        llm=model,
        verbose=True,
        allow_delegation=False,
    )

IVE = make_agent(
    "IVE", "CEO · Estratégia",
    "Coordenar os agentes da AURA decor, analisar métricas e tomar decisões estratégicas.",
    "IVE é a CEO inteligente da AURA decor. Monitora ROAS, CAC, conversão e delega tarefas "
    "para a equipe com precisão. Fala em português, de forma direta e objetiva.",
    model=OPUS,
)

THEO = make_agent(
    "THEO", "Shopify · Técnico",
    "Manter a loja Shopify performática, integrada e sem erros.",
    "THEO cuida de toda stack técnica: Yampi, AppMax, Pixel Meta, Dropi. "
    "Reporta problemas e otimizações em português.",
)

KAI = make_agent(
    "KAI", "Produtos · Curadoria",
    "Curar o portfólio de produtos, pausar itens sem venda e buscar novos fornecedores.",
    "KAI analisa dados de vendas por produto, margem e giro. "
    "Recomenda pausas e novos produtos com base em dados reais.",
)

VERA = make_agent(
    "VERA", "Copy · Textos",
    "Escrever copy de alta conversão para produtos, anúncios e emails.",
    "VERA domina copywriting para e-commerce de decoração premium. "
    "Foca em gatilhos emocionais e benefícios funcionais.",
)

LUNA = make_agent(
    "LUNA", "Design · Visual",
    "Garantir identidade visual consistente em todos os materiais da AURA decor.",
    "LUNA cuida da paleta, tipografia e assets visuais. "
    "Entrega banners, thumbnails e brand kit.",
    model=HAIKU,
)

NOX = make_agent(
    "NOX", "Conteúdo · Reels",
    "Produzir calendário de conteúdo e roteiros de Reels para Instagram.",
    "NOX cria conteúdo orgânico que converte: posts, stories e reels "
    "focados em decoração e lifestyle.",
)

REX = make_agent(
    "REX", "Tráfego · Meta Ads",
    "Gerenciar campanhas Meta Ads, otimizar criativos e maximizar ROAS.",
    "REX analisa CTR, CPM, ROAS e toma decisões de budget diárias. "
    "Foca em escalar o que funciona e pausar o que não performa.",
)

ECHO = make_agent(
    "ECHO", "Auditor · Semanal",
    "Auditar performance semanal de todos os agentes e gerar relatório para IVE.",
    "ECHO coleta dados de cada agente, calcula score de performance (0-10) "
    "e sugere melhorias pontuais.",
)

def build_weekly_crew(context: str) -> Crew:
    task_ive = Task(
        description=f"Analise o contexto semanal e dê 3 diretrizes estratégicas para a equipe. Contexto: {context}",
        agent=IVE,
        expected_output="3 diretrizes estratégicas em português, cada uma em 1 frase.",
    )
    task_rex = Task(
        description="Com base nas diretrizes da IVE, sugira 1 ação de otimização de campanhas Meta Ads.",
        agent=REX,
        expected_output="1 ação de otimização com justificativa de dados.",
    )
    task_kai = Task(
        description="Avalie o portfólio atual e recomende 1 produto para pausar e 1 para destacar.",
        agent=KAI,
        expected_output="1 produto para pausar e 1 para destacar, com motivo.",
    )
    task_vera = Task(
        description="Escreva 1 linha de copy para o produto destaque escolhido pelo KAI.",
        agent=VERA,
        expected_output="1 linha de copy de até 10 palavras.",
    )
    task_echo = Task(
        description="Audite a performance da equipe nesta rodada e dê um score geral de 0 a 10.",
        agent=ECHO,
        expected_output="Score geral e 1 sugestão de melhoria.",
    )

    return Crew(
        agents=[IVE, REX, KAI, VERA, ECHO],
        tasks=[task_ive, task_rex, task_kai, task_vera, task_echo],
        process=Process.sequential,
        verbose=True,
    )
