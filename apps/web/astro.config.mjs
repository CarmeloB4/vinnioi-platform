import { defineConfig } from 'astro/config';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig({
  site: 'https://vinnioi.it',
  output: 'static',
  outDir: process.env.VINNIOI_OUT_DIR || './dist',
  vite: { plugins: [tailwindcss()] },
});
