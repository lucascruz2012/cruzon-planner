# CruzInvest

Acompanhamento da carteira de investimentos: patrimônio, rentabilidade, comparação com o CDI, proventos e um **semáforo de saúde** por ativo (🟢 saudável · 🟡 atenção · 🔴 risco).

**Endereço (depois de publicar no GitHub Pages):** `https://lucascruz2012.github.io/cruzon-planner/cruzinvest/`

## Primeiros passos

1. Abra o endereço e crie seu **cofre** (nome, e-mail e senha forte; depois o login é por e-mail e senha). Não existe recuperação de senha: guarde-a bem.
2. Em **Ajustes → Fonte de dados**, cole o token gratuito da [brapi.dev](https://brapi.dev/dashboard). Sem ele, só alguns ativos (PETR4, VALE3, ITUB4…) têm cotação.
   O plano gratuito não inclui proventos: o app detecta isso sozinho e usa só o que o plano libera. Registre ou importe dividendos e rendimentos na aba **Proventos** (planilha com Ativo, Data com/Pagamento e Valor por cota ou Valor total).
3. Em **Lançamentos → Importar da B3**, selecione de uma vez os arquivos Excel da Área do Investidor (investidor.b3.com.br):
   - **Extratos → Negociação** (maior período disponível): compras e vendas;
   - **Relatórios → Consolidado mensal** (pode mandar todos os meses; o mais recente confere a posição);
   - **Extratos → Movimentação** (opcional): proventos, bonificações e desdobramentos.

   Para cotas compradas antes do período do extrato de negociação, o app pede o preço médio atual (o da corretora ou do Investidor10) e calcula o resto.
   Também é possível usar **Importar planilha** com um CSV `Ativo; Quantidade; Preço` (opcionais: `Data`, `Operação`, `Taxas`, `Classe`).
4. Toque em ↻ para buscar cotações, indicadores e proventos. O app também atualiza sozinho ao abrir, se os dados estiverem velhos.
5. Em **Ajustes → Backup**, baixe um backup criptografado de tempos em tempos.

## Segurança

- Os dados ficam **criptografados no aparelho** (AES-256-GCM; chave derivada da senha por PBKDF2-SHA-256 com 310 mil iterações). A senha e a chave nunca são gravadas.
- O app se bloqueia sozinho após o tempo de inatividade escolhido. Depois de 5 senhas erradas, impõe uma espera crescente.
- Nenhum dado da carteira é enviado a servidores. O app só consulta cotações por ticker na brapi e índices no Banco Central.

## O que é analisado

| Classe | Indicadores e alertas |
|---|---|
| Ações e BDRs | P/L (prejuízo ou caro), P/VP, ROE, margem líquida, dívida líquida/EBITDA, liquidez corrente, payout acima de 100% (os três últimos não se aplicam a bancos e seguradoras) |
| FIIs | DY 12m (baixo, ou alto demais, o que pode indicar rendimento não recorrente), queda do rendimento recente frente ao histórico, P/VP (informe o VP por cota) |
| Carteira | Concentração por ativo, queda desde a máxima de 52 semanas, queda forte num pregão |

Todos os limites podem ser ajustados em **Ajustes → Limites da análise**. Os alertas são filtros de atenção, não recomendação de compra ou venda.

## Fontes

- [brapi.dev](https://brapi.dev): cotações, indicadores fundamentalistas e proventos.
- [Banco Central (SGS)](https://dadosabertos.bcb.gov.br): CDI diário (série 12), Selic meta (432) e IPCA 12 meses (13522).
