# 머머월드 블로그 · Murmurworld

머머월드(Murmurworld)는 신혼집 살림, 집 밖에서 만난 장소, 머머월드의 이야기와 영상을 담는 Astro 블로그입니다. 주식 지도에서는 기업이 무엇을 팔고 어디에서 사업을 하는지 공시와 함께 살펴볼 수 있습니다. [머머월드](https://murmurworld.github.io/) · [주식 지도](https://murmurworld.github.io/stocks/)

## 미리보기

저장소를 처음 내려받았다면 PowerShell에서 아래 명령으로 배포본과 같은 원고와 데이터를 준비합니다. `site`는 미리보기용 폴더입니다.

```powershell
python -m zipfile -e murmurworld-source.zip site
Copy-Item src/articles -Destination site/src -Recurse -Force
New-Item -ItemType Directory -Force site/public/data/company-reports | Out-Null
Copy-Item public/data/company-reports/*.json site/public/data/company-reports
Copy-Item public/data/etf-holdings.json site/src/site/etf-holdings.json
Set-Location site
```

미리보기 폴더에서 Node.js 24와 pnpm 11.25.0으로 실행합니다.

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

소유자가 보관한 바로가기로 블로그 관리 화면을 열고 수정할 글과 언어를 고릅니다. 저장소 쓰기 권한이 있는 GitHub 계정으로 원고를 `main`에 저장하면 GitHub Actions가 블로그를 다시 배포합니다. 관리 화면의 경로는 저장소의 Actions secret `MURMURWORLD_OWNER_ROUTE`로 설정합니다.

디자인이나 기능을 바꿀 때는 `murmurworld-source.zip`을 교체합니다. 배포 때는 저장소의 `src/articles/`에 있는 최신 원고를 복사합니다. 예를 들어 인텔 본문을 고치려면 `src/articles/companies/semiconductors/intel.ko.md`를 수정하고, 영어판은 옆의 `intel.en.md`에서 같은 내용을 반영합니다. GitHub에서 해당 파일을 열어 연필을 누르고 저장하면 됩니다.

기업 공시와 ETF 보유 목록은 GitHub Actions의 **Monthly public company filings**에서 매달 1일 한국 시간 오전 9시 43분에 갱신을 시작하도록 예약되어 있습니다. 같은 화면의 **Run workflow**로 직접 실행할 수도 있습니다. 실행 요약에 확인한 출처와 이전 자료를 유지한 항목이 나옵니다. 화면에 표시되는 기준일은 각 회사나 운용사가 발표한 자료의 날짜입니다.

방문 통계는 Cloudflare Web Analytics 사이트 토큰을 GitHub Actions 저장소 변수 `PUBLIC_CLOUDFLARE_WEB_ANALYTICS_TOKEN`에 등록하고 워크플로를 다시 실행하면 집계됩니다.

[Astro GitHub Pages 공식 안내](https://docs.astro.build/en/guides/deploy/github/)
