const path = require('path');

module.exports = {
  mode: 'development',
  entry: './js/main.js',
  output: {
    filename: 'bundle.js',
    path: path.resolve(__dirname, 'dist'),
    clean: false,
  },
  devServer: {
    static: {
      directory: path.join(__dirname, '.'),
    },
    compress: true,
    port: 8000,
    hot: false,
    open: false,
    historyApiFallback: true,
    allowedHosts: 'all',
  },
  devtool: 'source-map',
  resolve: {
    extensions: ['.js'],
  },
};
