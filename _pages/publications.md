---
layout: archive
title: "Publications"
permalink: /publications/
author_profile: true
---

{% if author.googlescholar %}
  You can also find my articles on <u><a href="{{author.googlescholar}}">my Google Scholar profile</a>.</u>
{% endif %}

{% include base_path %}

{% comment %}
The existing _publications collection remains available as a fallback until
ORCID has imported records. Once synced, show only the ORCID list so manually
curated publications don't appear twice on this page.
{% endcomment %}
{% assign orcid_works = site.data.orcid_publications %}
{% if orcid_works and orcid_works.size > 0 %}
  {% include orcid-publications.html %}
{% else %}
  {% for post in site.publications reversed %}
    {% include archive-single.html %}
  {% endfor %}
{% endif %}
