const path = require('path');
const webpack = require('webpack');
const TerserPlugin = require('terser-webpack-plugin');

module.exports = (env, argv) => {
    let mode = 'production';
    if (argv.mode) {
        mode = argv.mode;
    }

    return {
        mode: mode,
        entry: {
            main: './src/lib/index.js'
        },
        output: {
            path: path.resolve(__dirname, 'dash_component_editor'),
            filename: mode === 'development' ? 'dash_component_editor.dev.js' : 'dash_component_editor.min.js',
            library: 'dash_component_editor',
            libraryTarget: 'window',
        },
        externals: {
            react: 'React',
            'react-dom': 'ReactDOM',
            'prop-types': 'PropTypes',
        },
        module: {
            rules: [
                {
                    test: /\.(ts|tsx)$/,
                    use: [
                        {
                            loader: 'babel-loader',
                            options: {
                                presets: [
                                    '@babel/preset-env',
                                    '@babel/preset-react',
                                    '@babel/preset-typescript'
                                ]
                            }
                        },
                        {
                            loader: 'ts-loader',
                            options: {
                                transpileOnly: true
                            }
                        }
                    ],
                    exclude: /node_modules/,
                },
                {
                    test: /\.js$/,
                    exclude: /node_modules/,
                    use: {
                        loader: 'babel-loader',
                        options: {
                            presets: ['@babel/preset-env', '@babel/preset-react']
                        }
                    }
                },
                {
                    test: /\.css$/,
                    use: [
                        'style-loader',
                        'css-loader',
                        'postcss-loader'
                    ],
                }
            ]
        },
        resolve: {
            extensions: ['.ts', '.tsx', '.js', '.jsx', '.json'],
            alias: {
                '@': path.resolve(__dirname, 'src/lib/internal')
            }
        },
        optimization: {
            minimizer: [
                new TerserPlugin({
                    parallel: true,
                    terserOptions: {
                        compress: {
                            drop_console: mode === 'production' // Only drop console in production
                        }
                    }
                })
            ]
        },
        plugins: [
            new webpack.DefinePlugin({
                'process.env.NODE_ENV': JSON.stringify(mode)
            })
        ]
    };
};
