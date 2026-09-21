import React from "react";
import { Message } from "./Message";
import { LoadingIndicator } from "./LoadingIndicator";

const ChatWindow = ({ messages, isTyping, typingMessage, isLoading, loadingLabel, error, messagesEndRef, onSendDirect }) => (
  <div>
    {messages.map((message, index) => (
      <Message
        key={index}
        message={message.text}
        isUser={message.isUser}
        content={message.content}
        followUps={message.followUps}
        onSendDirect={onSendDirect}
      />
    ))}
    {isTyping && typingMessage && (
      <Message message={typingMessage} isUser={false} content={[]} />
    )}
    {isLoading && <LoadingIndicator label={loadingLabel} />}
    {error && (
      <div style={{ textAlign: "center", fontSize: 13, color: "#f87171", padding: "8px 0" }}>{error}</div>
    )}
    <div ref={messagesEndRef} />
  </div>
);

export default ChatWindow;
