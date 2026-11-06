import { getPost } from "../writing";
import styles from "./BlogPost.module.css";

type Block = { list: false; text: string } | { list: true; items: string[] };

// Paragraphs are split by blank lines; a run of lines starting with "- " is a bulleted list.
function blocks(content: string): Block[] {
  const out: Block[] = [];
  for (const para of content.split(/\n\s*\n/)) {
    let text: string[] = [];
    let items: string[] = [];
    const flush = () => {
      if (text.length) out.push({ list: false, text: text.join("\n") });
      if (items.length) out.push({ list: true, items });
      text = [];
      items = [];
    };
    for (const line of para.split("\n")) {
      if (line.startsWith("- ")) {
        if (text.length) flush();
        items.push(line.slice(2));
      } else {
        if (items.length) flush();
        text.push(line);
      }
    }
    flush();
  }
  return out;
}

export default function BlogPost({ slug }: { slug: string }) {
  const post = getPost(slug);

  if (!post) return <div className={styles.blog}>Post not found.</div>;

  return (
    <div className={styles.blog}>
      <div className={styles.title}>{post.title}</div>
      {post.subtitle && <div className={styles.subtitle}>{post.subtitle}</div>}
      <div className={styles.date}>{post.date}</div>
      {post.image && (
        // eslint-disable-next-line @next/next/no-img-element
        <img className={styles.image} src={post.image} alt="" />
      )}
      <div className={styles.content}>
        {blocks(post.content).map((b, i) =>
          b.list ? (
            <ul key={i} className={styles.list}>
              {b.items.map((item, j) => <li key={j}>{item}</li>)}
            </ul>
          ) : (
            <p key={i} className={styles.paragraph}>{b.text}</p>
          ),
        )}
      </div>
    </div>
  );
}
