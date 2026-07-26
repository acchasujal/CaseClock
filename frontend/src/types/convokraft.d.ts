declare namespace JSX {
  interface IntrinsicElements {
    'convokraft-chat-bot': React.DetailedHTMLProps<React.HTMLAttributes<HTMLElement>, HTMLElement> & {
      'bot-name'?: string
      'project-id'?: string
      'org-id'?: string
    }
  }
}
