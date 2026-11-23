# 머머월드 블로그 · Murmurworld

머머월드(Murmurworld)는 결혼·신혼 준비와 집관리, 맛집과 가볼 만한 곳, 같은 이름의 가상 세계를 소개하는 글과 영상을 담는 Astro 블로그입니다. 공식 주소는 `https://murmurworld.github.io`입니다.

## 미리보기

Node.js 24와 pnpm 11.25.0으로 빌드합니다. `blog-site` 폴더에서 실행하세요.

```sh
pnpm install --frozen-lockfile
pnpm dev
```

`http://localhost:4321/blog/`에서 블로그를 엽니다. 파일을 저장하면 개발 서버가 화면을 갱신합니다. 배포용 파일은 `pnpm build`로 `dist/`에 만듭니다.

## 디자인과 내용 수정

- `src/layouts/Base.astro`와 `src/styles/site.css`에서 메뉴, 색, 글꼴을 수정합니다.
- `src/pages/index.astro`는 머머월드 홈이고, `src/pages/blog/index.astro`는 블로그의 주제별 입구입니다. 세계관과 영상은 `src/pages/blog/murmurworld/`에서 관리합니다.
- 계산기 화면은 `src/calc/index.html`, 계산 코드와 데이터는 `public/calc/`에 있습니다. `pnpm sync-calc`는 원본 계산기 폴더(`C:/dev/elec-calc`)에서 변경 내용을 다시 가져올 때만 실행합니다.

## GitHub Pages 배포

`murmurworld/murmurworld.github.io` 저장소의 **Settings → Pages → Source**는 **GitHub Actions**를 사용합니다. 사이트 소스를 수정한 뒤 `main`의 `murmurworld-source.zip`을 새 파일로 교체하면 Actions가 빌드해 배포합니다.

[Astro GitHub Pages 공식 안내](https://docs.astro.build/en/guides/deploy/github/)
