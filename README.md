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

집꾸미기 글의 제목·요약·본문은 [블로그 관리 화면](https://murmurworld.github.io/admin/)에서 선택한 뒤 GitHub에 로그인해 고칠 수 있습니다. 저장소의 쓰기 권한이 있는 계정이 `src/articles/home-decor/`의 한·영 원고를 `main`에 저장하면 GitHub Actions가 공개 사이트를 다시 배포합니다. 검토가 필요하면 새 브랜치에 저장한 뒤 검토하고 `main`에 합칩니다.

디자인이나 기능을 바꿀 때는 `murmurworld/murmurworld.github.io` 저장소의 `murmurworld-source.zip`을 교체합니다. 새 ZIP을 풀고 나면 Actions가 저장소에 있는 집꾸미기 원고를 빌드 폴더에 복사합니다. 이후 원고 수정은 관리 화면에서 연결한 Markdown에 반영합니다.

방문 통계는 Cloudflare Web Analytics 사이트 토큰을 GitHub Actions 저장소 변수 `PUBLIC_CLOUDFLARE_WEB_ANALYTICS_TOKEN`에 등록하고 워크플로를 다시 실행하면 집계됩니다.

[Astro GitHub Pages 공식 안내](https://docs.astro.build/en/guides/deploy/github/)
