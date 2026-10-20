# Aline Pumps static staging mockup

The migration pages use copy and selected images from `../current-site-backup/`.
Product category and product paths follow the pre-migration SEO baseline. Projects,
articles and article categories retain their current paths. The original eight
hand-built pages remain available as flat `.html` files, with copies at their
planned clean paths.

Rebuild generated pages after changing the backup or templates:

```sh
python3 scripts/build_remaining_pages.py
python3 scripts/update_existing_pages.py
```

Run the scripts in this order. The second script restores the custom KUSP40 and
undersink category layouts at their clean paths. All pages carry `noindex,
nofollow` while this is a staging mockup; remove that directive only at launch.
The contact and training forms use the original HubSpot embeds and require
network access to load. Product, service and project enquiry links pass context
in the contact URL, including the HubSpot `message` field.

## Staging deployment

The committed HTML and assets are deployed to GitHub Pages when `main` is pushed,
or when **Deploy staging site** is run manually in GitHub Actions. The workflow
publishes only HTML, assets and `.nojekyll`. Set the repository's Pages source to
**GitHub Actions**. The expected staging URL is
`https://lilmonstersam.github.io/aline-pumps-staging-site/`.

The source backup and SEO inventory sit outside this repository, so GitHub
Actions deploys the committed output rather than rebuilding it. Run the two
scripts above locally and commit the resulting pages after template or copy
changes. The site remains marked `noindex, nofollow` for staging.
