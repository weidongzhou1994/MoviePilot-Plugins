// Hello World example

function main() {
  console.log('Hello, world!');
}

if (require.main === module) {
  main();
}

module.exports = { main };
