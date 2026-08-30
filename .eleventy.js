module.exports = function (eleventyConfig) {
  eleventyConfig.addPassthroughCopy("css");
  eleventyConfig.addPassthroughCopy("js");
  eleventyConfig.addPassthroughCopy("images");
  eleventyConfig.addPassthroughCopy("robots.txt");
  eleventyConfig.addPassthroughCopy("admin/config.yml");

  eleventyConfig.addCollection("services", (api) =>
    api
      .getFilteredByGlob("content/services/*.md")
      .sort((a, b) => (a.data.order || 0) - (b.data.order || 0))
  );

  eleventyConfig.addCollection("testimonials", (api) =>
    api
      .getFilteredByGlob("content/testimonials/*.md")
      .sort((a, b) => (a.data.order || 0) - (b.data.order || 0))
  );

  eleventyConfig.addCollection("galleryItems", (api) =>
    api
      .getFilteredByGlob("content/gallery/*.md")
      .sort((a, b) => (a.data.order || 0) - (b.data.order || 0))
  );

  eleventyConfig.addCollection("faqs", (api) =>
    api
      .getFilteredByGlob("content/faq/*.md")
      .sort((a, b) => (a.data.order || 0) - (b.data.order || 0))
  );

  return {
    dir: {
      input: ".",
      includes: "_includes",
      data: "_data",
      output: "_site",
    },
    templateFormats: ["html", "njk", "md"],
    htmlTemplateEngine: "njk",
    markdownTemplateEngine: "njk",
  };
};
