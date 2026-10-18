import { content } from '../content';
export default function Footer() {
  return (
    <footer className="bg-ink px-5 py-10 text-center text-sm text-paper/80">
      <p className="font-display text-lg text-paper">{content.brand}</p>
      <p className="mt-2">{content.footer}</p>
    </footer>
  );
}
