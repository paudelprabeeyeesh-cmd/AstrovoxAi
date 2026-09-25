import MarkdownRenderer from './MarkdownRenderer'

export default function MessageContent({ content }) {
  if (!content) return null
  return <MarkdownRenderer content={content} />
}
