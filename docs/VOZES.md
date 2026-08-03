# Vozes do estúdio (MiniMax via fal.ai)
- NARRADORA "Vera" (narradora de filmes de marcas premium):
  ID_NOVO_AQUI
- CETICA (apresentadora de podcast): resgatar com rid 019f535f-146a-74b1-8fed-5e07adecdb01
- Modelo TTS: fal-ai/minimax/speech-02-hd ($0.10/1k chars, pausas via <#x#>)

## Notas de resgate (22/07/2026)
- Voice ID da NARRADORA confirmado e testado no script generate_vo.py
- CETICA: voice_id ainda a resgatar via dashboard fal (Requests > rid acima)
- .env: FAL_KEY rotacionada em 22/07 (a antiga 46143ea8 deve ser revogada no painel)
- Teste rapido: python -m scripts.generate_vo "texto" --voice ID --name nome
