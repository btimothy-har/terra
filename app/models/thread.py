from uuid import uuid4

from langchain_core.messages import ChatMessage

from shared.models.thread import ConversationThread
from shared.models.thread import ThreadMessage


class AppThread(ConversationThread):

    @classmethod
    def create(cls, session_id) -> "AppThread":
        return cls(
            sid=session_id,
            thread_id=uuid4(),
            messages=[]
            )

    def append(self, message:ChatMessage) -> list[ChatMessage]:
        thread_msg = ThreadMessage.from_chat_message(message)
        self.messages.append(thread_msg)
        return self.messages
