interface Props {
  title: string;
  milestone: string;
}

export default function Placeholder({ title, milestone }: Props) {
  return (
    <div className="placeholder">
      <h2>{title}</h2>
      <p>该页面将于 <strong>{milestone}</strong> 阶段实装。</p>
    </div>
  );
}
