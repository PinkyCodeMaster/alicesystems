# assistant-runtime

- Purpose: Local assistant orchestration runtime.
- Will contain: STT, prompt assembly, tool calling, memory, and TTS modules.
- Responsibilities: Interpret user input and request actions through Home OS tools without direct device control.
- Interfaces: Reads context and invokes tools through authenticated Home OS APIs; uses Ollama, Whisper-class STT, and Piper locally.
- Status: in progress.
