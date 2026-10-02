// Tiny remark plugin: turns "[PLACEHOLDER...]" text into a highlighted span so
// unconfirmed claims are impossible to miss in rendered copy.
type Node = { type: string; value?: string; children?: Node[]; data?: Record<string, unknown> }
const RE = /\[PLACEHOLDER[^\]]*\]/g

export default function remarkPlaceholder() {
  return (tree: Node) => {
    const walk = (node: Node) => {
      if (!node.children) return
      const out: Node[] = []
      for (const child of node.children) {
        if (child.type === 'text' && child.value && RE.test(child.value)) {
          RE.lastIndex = 0
          let last = 0
          for (const m of child.value.matchAll(RE)) {
            if (m.index! > last) out.push({ type: 'text', value: child.value.slice(last, m.index) })
            out.push({
              type: 'placeholder',
              data: { hName: 'span', hProperties: { className: ['placeholder-tag'] } },
              children: [{ type: 'text', value: m[0] }],
            })
            last = m.index! + m[0].length
          }
          if (last < child.value.length) out.push({ type: 'text', value: child.value.slice(last) })
        } else {
          walk(child)
          out.push(child)
        }
      }
      node.children = out
    }
    walk(tree)
  }
}
