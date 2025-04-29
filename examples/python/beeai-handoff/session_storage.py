from acp_sdk import Message

class SessionStorage:
    messages: dict[str, list[Message]] = {}
        
    def append(self, session_id: str, message_list: list[Message]):
        self.messages[session_id] = message_list
    
    def get(self, session_id: str) -> list[Message]:
        return self.messages.get(session_id, [])
    