import { useRef } from 'react'
import { useEditor, EditorContent } from '@tiptap/react'
import StarterKit from '@tiptap/starter-kit'
import Image from '@tiptap/extension-image'
import Link from '@tiptap/extension-link'

interface EditorProps {
  content: string
  onChange: (html: string) => void
}

// 工具栏按钮统一封装
function ToolbarButton({
  active,
  onClick,
  children,
  title,
}: {
  active?: boolean
  onClick: () => void
  children: React.ReactNode
  title?: string
}) {
  return (
    <button
      type="button"
      title={title}
      onMouseDown={(e) => e.preventDefault()}
      onClick={onClick}
      className={`px-2 py-1 text-sm rounded hover:bg-gray-100 ${active ? 'bg-gray-200' : ''}`}
    >
      {children}
    </button>
  )
}

export default function Editor({ content, onChange }: EditorProps) {
  const fileInputRef = useRef<HTMLInputElement>(null)

  const editor = useEditor({
    extensions: [
      StarterKit,
      Image.configure({ inline: false, allowBase64: true }),
      Link.configure({ openOnClick: false, HTMLAttributes: { rel: 'noopener' } }),
    ],
    content,
    onUpdate: ({ editor }) => {
      onChange(editor.getHTML())
    },
  })

  if (!editor) {
    return <p className="text-gray-400 p-6">编辑器加载中...</p>
  }

  const addImage = (file: File) => {
    const reader = new FileReader()
    reader.onload = () => {
      const src = reader.result as string
      editor.chain().focus().setImage({ src }).run()
    }
    reader.readAsDataURL(file)
  }

  const addLink = () => {
    const prev = editor.getAttributes('link').href
    const url = window.prompt('链接地址：', prev || 'https://')
    if (!url) return
    if (url === '') {
      editor.chain().focus().unsetLink().run()
      return
    }
    editor.chain().focus().extendMarkRange('link').setLink({ href: url }).run()
  }

  const setImageByUrl = () => {
    const url = window.prompt('图片 URL：', 'https://')
    if (!url) return
    editor.chain().focus().setImage({ src: url }).run()
  }

  return (
    <div className="flex flex-col h-full bg-white">
      {/* 工具栏 */}
      <div className="flex flex-wrap items-center gap-1 border-b border-gray-200 px-3 py-1.5">
        {/* 撤销/重做 */}
        <ToolbarButton title="撤销" onClick={() => editor.chain().focus().undo().run()}>
          ↩
        </ToolbarButton>
        <ToolbarButton title="重做" onClick={() => editor.chain().focus().redo().run()}>
          ↪
        </ToolbarButton>

        <span className="mx-1 text-gray-300">|</span>

        {/* 文本样式 */}
        <ToolbarButton
          title="加粗"
          active={editor.isActive('bold')}
          onClick={() => editor.chain().focus().toggleBold().run()}
        >
          <strong>B</strong>
        </ToolbarButton>
        <ToolbarButton
          title="斜体"
          active={editor.isActive('italic')}
          onClick={() => editor.chain().focus().toggleItalic().run()}
        >
          <em>I</em>
        </ToolbarButton>
        <ToolbarButton
          title="删除线"
          active={editor.isActive('strike')}
          onClick={() => editor.chain().focus().toggleStrike().run()}
        >
          <s>S</s>
        </ToolbarButton>
        <ToolbarButton
          title="行内代码"
          active={editor.isActive('code')}
          onClick={() => editor.chain().focus().toggleCode().run()}
        >
          {'</>'}
        </ToolbarButton>

        <span className="mx-1 text-gray-300">|</span>

        {/* 标题 */}
        <ToolbarButton
          title="一级标题"
          active={editor.isActive('heading', { level: 1 })}
          onClick={() => editor.chain().focus().toggleHeading({ level: 1 }).run()}
        >
          H1
        </ToolbarButton>
        <ToolbarButton
          title="二级标题"
          active={editor.isActive('heading', { level: 2 })}
          onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()}
        >
          H2
        </ToolbarButton>
        <ToolbarButton
          title="三级标题"
          active={editor.isActive('heading', { level: 3 })}
          onClick={() => editor.chain().focus().toggleHeading({ level: 3 }).run()}
        >
          H3
        </ToolbarButton>

        <span className="mx-1 text-gray-300">|</span>

        {/* 列表 */}
        <ToolbarButton
          title="无序列表"
          active={editor.isActive('bulletList')}
          onClick={() => editor.chain().focus().toggleBulletList().run()}
        >
          • 列表
        </ToolbarButton>
        <ToolbarButton
          title="有序列表"
          active={editor.isActive('orderedList')}
          onClick={() => editor.chain().focus().toggleOrderedList().run()}
        >
          1. 列表
        </ToolbarButton>

        <span className="mx-1 text-gray-300">|</span>

        {/* 引用 / 代码块 / 分割线 */}
        <ToolbarButton
          title="引用"
          active={editor.isActive('blockquote')}
          onClick={() => editor.chain().focus().toggleBlockquote().run()}
        >
          ❝ 引用
        </ToolbarButton>
        <ToolbarButton
          title="代码块"
          active={editor.isActive('codeBlock')}
          onClick={() => editor.chain().focus().toggleCodeBlock().run()}
        >
          {'{}'} 代码块
        </ToolbarButton>
        <ToolbarButton
          title="分割线"
          onClick={() => editor.chain().focus().setHorizontalRule().run()}
        >
          ― 分割线
        </ToolbarButton>

        <span className="mx-1 text-gray-300">|</span>

        {/* 链接 / 图片 */}
        <ToolbarButton
          title="插入链接"
          active={editor.isActive('link')}
          onClick={addLink}
        >
          🔗 链接
        </ToolbarButton>
        <ToolbarButton title="上传图片" onClick={() => fileInputRef.current?.click()}>
          🖼 图片
        </ToolbarButton>
        <ToolbarButton title="图片 URL" onClick={setImageByUrl}>
          🔗 图片URL
        </ToolbarButton>

        {/* 隐藏的文件输入 */}
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          className="hidden"
          onChange={(e) => {
            const file = e.target.files?.[0]
            if (file) addImage(file)
            e.target.value = ''
          }}
        />
      </div>

      {/* 编辑区 */}
      <EditorContent editor={editor} className="flex-1 overflow-y-auto px-6 py-4" />
    </div>
  )
}
