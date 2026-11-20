import {textElement} from './sources.js';

export function recoveryText(error) {
  if (error?.status === 429) return 'The service is busy right now. Give it a moment, then try again. Your question is still here.';
  if (error?.status === 404) return 'I could not reopen that saved conversation. Start a new conversation to continue; your other saved investigations are still available.';
  if (error?.name === 'AbortError' || /timed out/i.test(error?.message || '')) return 'That took longer than expected. Please try a shorter question, or try again in a moment.';
  return 'I could not reach the answer service just now. Check that the project terminal is running, then try again. I have kept your question so you do not have to type it again.';
}

export function renderChatProblem(question, error, retry) {
  const item = textElement('article', undefined, 'message chat-problem');
  item.append(textElement('div', question, 'user-question'));
  const bubble = textElement('div', undefined, 'answer-card');
  bubble.append(textElement('strong', 'Parts assistant', 'chat-speaker'), textElement('p', recoveryText(error), 'claim'));
  const button = textElement('button', 'Try again', 'outline-button'); button.type = 'button'; button.onclick = retry;
  bubble.append(button); item.append(bubble); return item;
}
