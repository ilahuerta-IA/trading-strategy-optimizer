# Advanced Quantitative Trading Platform

## Overview

This project provides a comprehensive **Python-based framework** for backtesting and analyzing sophisticated quantitative trading strategies. Built around the powerful **Backtrader** engine, it offers multiple interfaces for strategy development, testing, and portfolio analysis:

### 🔧 **Three Main Interfaces:**

1. **📊 Individual Strategy Execution:** Direct strategy scripts for focused testing and development
2. **🖥️ Command-Line Tool (`main.py`):** Advanced CLI with interactive HTML reporting 
3. **🌐 Web Application (`app_server.py`):** Browser-based interface with real-time backend processing

### 🎯 **Key Features:**

- **🤖 AI-Powered Trading Strategies** with Transformer and LSTM models
- **📈 Advanced Portfolio Management** with dual-asset cerebro implementation  
- **📊 Interactive Visualization** with mouse-hover charts and real-time data display
- **⚡ Asynchronous Processing** for non-blocking web-based backtesting
- **🎨 Professional HTML Reports** with Lightweight Charts™ integration
- **🔄 Modular Strategy System** for easy development and testing

## 🏗️ Architecture Overview

The platform supports three distinct execution modes, each optimized for different use cases:

### Mode 1: Direct Strategy Execution 🎯
```bash
# Run individual strategies directly for development and testing
python src/strategies/dual_asset_strategy.py
python src/strategies/transformer_signal_strategy.py  
python src/strategies/lstm_signal_strategy.py
```

**Features:**
- ✅ **Dual Asset Portfolio Trading** - EURUSD + USDCHF with independent cerebro instances
- ✅ **Interactive Charts** - Mouse hover with real-time price/date display  
- ✅ **Portfolio Aggregation** - Combined performance analysis and risk metrics
- ✅ **AI Trading Integration** - Pre-trained Transformer and LSTM models
- ✅ **Advanced Risk Management** - Drawdown analysis, Sharpe ratios, win rates

### Mode 2: Command-Line Interface 🖥️
```bash
# Generate comprehensive HTML reports with advanced visualizations
python main.py --plot --fromdate 2023-01-01 --strat "p_fast_d0=15"
```

**Features:**
- 📊 **Self-Contained HTML Reports** - Portable analysis with embedded charts
- 🎨 **Lightweight Charts™ Integration** - Professional-grade financial visualizations  
- ⚙️ **Advanced Parameter Control** - Full strategy customization via CLI arguments
- 📈 **Comprehensive Analytics** - Trade analysis, performance metrics, indicators

### Mode 3: Web Application 🌐
```bash
# Launch interactive web-based backtesting platform
python src/app_server.py
```

**Features:**
- 🌐 **Browser-Based Interface** - Easy access via http://127.0.0.1:5000/
- ⚡ **Asynchronous Backend** - Non-blocking processing with SQLite task management
- 🔄 **Dynamic Configuration** - Real-time parameter adjustment and strategy selection
- 📊 **Statistical Reporting** - Detailed numerical analysis and performance metrics

## 📁 Project Structure

```
📦 quant_bot_project/
┣ 📂 src/                          # Core application modules
┃ ┣ 📄 app_server.py              # 🌐 Flask web server & API endpoints
┃ ┣ 📄 worker.py                  # ⚡ Background async task processor  
┃ ┣ 📄 database.py                # 🗃️ SQLite database management
┃ ┣ 📄 train_transformer.py       # 🤖 ML model training pipeline
┃ ┣ 📂 strategies/                # 📈 Trading strategy implementations
┃ ┃ ┣ 📄 dual_asset_strategy.py   # 🎯 EURUSD+USDCHF portfolio system
┃ ┃ ┣ 📄 transformer_signal_strategy.py # 🤖 AI Transformer trading
┃ ┃ ┣ 📄 lstm_signal_strategy.py  # 🧠 LSTM neural network strategy
┃ ┃ ┣ 📄 macd_signal_strategy.py  # 📊 Technical analysis strategies
┃ ┃ ┗ 📄 ... (additional strategies)
┃ ┣ 📂 ml_models/                 # 🤖 Trained model artifacts (.pth, .pkl)
┃ ┣ 📂 visualization/             # 📊 Chart generation & HTML reports
┃ ┃ ┣ 📄 web_plotter.py          # 🎨 Lightweight Charts™ integration
┃ ┃ ┗ 📄 report_template.html     # 📋 HTML report template
┃ ┣ 📂 backtesting/              # ⚙️ Core backtest execution engine
┃ ┃ ┗ 📄 runner.py               # 🚀 Backtrader integration layer
┃ ┣ 📂 utils/                    # 🛠️ Utility functions & helpers
┃ ┃ ┗ 📄 serialization.py        # 💾 JSON serialization utilities
┃ ┗ 📂 templates/                # 🌐 Web interface templates
┃   ┗ 📄 index.html              # 🖥️ Main web application UI
┣ 📄 main.py                     # 🖥️ CLI entry point & report generator
┣ 📂 data/                       # 📊 Financial data files (CSV format)
┣ 📄 requirements.txt            # 📦 Python dependencies specification
┗ 📄 README.MD                   # 📚 Project documentation (this file)
```

## 🔧 Prerequisites & Quick Start

### System Requirements
- **Python 3.8+** (Tested with Python 3.8-3.11)
- **Minimum 4GB RAM** (Recommended 8GB+ for ML strategies)
- **Windows/Linux/macOS** (Cross-platform compatible)

### ⚡ Quick Installation
```bash
# 1. Clone the repository
git clone <your-repo-url>
cd quant_bot_project

# 2. Install all dependencies
pip install -r requirements.txt

# 3. Verify installation by running a strategy
python src/strategies/dual_asset_strategy.py
```

### 🎯 Usage Examples

#### **Run Individual Strategies (Recommended for Development)**
```bash
# Interactive dual-asset portfolio with EURUSD + USDCHF
python src/strategies/dual_asset_strategy.py

# AI-powered Transformer strategy
python src/strategies/transformer_signal_strategy.py

# LSTM neural network strategy  
python src/strategies/lstm_signal_strategy.py
```

#### **Generate HTML Reports with CLI**
```bash
# Basic report generation
python main.py --plot

# Advanced parameter customization
python main.py --plot --fromdate 2023-01-01 --todate 2023-12-31 --strat "p_fast_d0=15,p_slow_d0=30"
```

#### **Launch Web Application**
```bash
# Start web server
python src/app_server.py

# Open browser to http://127.0.0.1:5000/
```

## 🎯 Detailed Usage Guide

### 🤖 **1. AI-Powered Strategies (Machine Learning)**

#### **Training Models** 
```bash
# Train Transformer model for time series prediction
python src/train_transformer.py

# Models are saved to src/ml_models/ directory
```

#### **Running AI Strategies**
```bash
# Use pre-trained Transformer model for trading signals
python src/strategies/transformer_signal_strategy.py

# LSTM neural network strategy with technical indicators
python src/strategies/lstm_signal_strategy.py
```

### 📈 **2. Portfolio & Multi-Asset Strategies**

#### **Dual Asset Portfolio (EURUSD + USDCHF)**
```bash
# Run comprehensive dual-asset portfolio analysis
python src/strategies/dual_asset_strategy.py
```

**Key Features:**
- ✅ **Independent Cerebro Instances** - Separate strategy execution per asset
- ✅ **Portfolio Aggregation** - Combined performance and risk analysis  
- ✅ **Interactive Charts** - Mouse hover with real-time data display
- ✅ **Risk Metrics** - Sharpe ratio, drawdown analysis, win rates

### 🖥️ **3. Command-Line Interface (Advanced Users)**

#### **Basic Report Generation**
```bash
# Generate interactive HTML report with default parameters
python main.py --plot
```

#### **Advanced Configuration**
```bash
# Custom date range and strategy parameters
python main.py --plot --fromdate 2023-01-01 --todate 2023-12-31 --strat "p_fast_d0=15,p_slow_d0=30"

# Multiple data files and custom cash
python main.py --plot --data "EURUSD_1h.csv,USDCHF_1h.csv" --cash 50000
```

**CLI Arguments:**
- `--plot` - Generate HTML report with Lightweight Charts™
- `--fromdate` / `--todate` - Date range (YYYY-MM-DD format)
- `--strat` - Strategy parameters (comma-separated)
- `--data` - Data file names (supports multiple files)
- `--cash` - Initial capital amount

### 🌐 **4. Web Application (User-Friendly Interface)**

#### **Starting the Server**
```bash
# Launch Flask web application
python src/app_server.py
```

#### **Using the Web Interface**
1. **Access:** Open browser to `http://127.0.0.1:5000/`
2. **Configure:** Select data files, date ranges, and strategy parameters
3. **Execute:** Start backtest with asynchronous processing
4. **Analyze:** View detailed statistical reports and performance metrics

**Web Features:**
- 🌐 **Browser-Based UI** - No command-line required
- ⚡ **Asynchronous Processing** - Non-blocking backtests
- 🔄 **Dynamic Configuration** - Real-time parameter adjustment
- 📊 **Statistical Analysis** - Comprehensive numerical reports
## 🔬 **Advanced Features & Configurations**

### 🤖 **Machine Learning Integration**

This platform includes sophisticated **AI-powered trading strategies** with pre-trained models:

#### **Time Series Transformer** 
- **Model:** Attention-based architecture for financial time series prediction
- **Training Data:** EUR/USD 5-minute timeframe with technical indicators
- **Usage:** `python src/strategies/transformer_signal_strategy.py`
- **Research Repository:** [Applied ML Trading Transformer for EUR/USD](https://github.com/ilahuerta-IA/applied-ml-trading-transformer-eurusd.git)

#### **LSTM Neural Networks**
- **Model:** Recurrent neural networks optimized for sequential financial data
- **Features:** Multi-timeframe analysis with technical indicator integration
- **Usage:** `python src/strategies/lstm_signal_strategy.py`

### 📊 **Strategy Development**

#### **Adding New Strategies**
```python
# Template for new strategy development
from backtrader import Strategy
import backtrader.indicators as btind

class MyCustomStrategy(Strategy):
    params = (
        ('period', 14),
        ('threshold', 0.02),
    )
    
    def __init__(self):
        self.indicator = btind.RSI(period=self.params.period)
    
    def next(self):
        if self.indicator > (100 - self.params.threshold):
            self.sell()
        elif self.indicator < self.params.threshold:
            self.buy()
```

#### **Strategy Registration**
1. Place strategy file in `src/strategies/` directory
2. The system automatically discovers and integrates new strategies
3. Parameters become available in both CLI and web interfaces

### ⚙️ **Configuration & Customization**

#### **Data Format Requirements**
```csv
# Expected CSV format for financial data
Date,Open,High,Low,Close,Volume
2023-01-01 00:00:00,1.0350,1.0365,1.0340,1.0355,1500
2023-01-01 01:00:00,1.0355,1.0370,1.0345,1.0360,1750
```

#### **Performance Optimization**
- **Memory Management:** Use `--maxcpus` for parallel processing
- **Data Sampling:** Configure date ranges to limit computational load  
- **Model Caching:** ML models are cached to avoid retraining
- **Async Processing:** Web interface uses background workers for responsiveness

### 📈 **Risk Management Features**

#### **Portfolio Analysis**
- **Sharpe Ratio:** Risk-adjusted return calculation
- **Maximum Drawdown:** Peak-to-trough decline analysis
- **Win Rate:** Percentage of profitable trades
- **Profit Factor:** Gross profit vs gross loss ratio

#### **Position Sizing**
- **Fixed Size:** Constant position sizing across trades
- **Percentage Risk:** Position sizing based on account percentage
- **Volatility Adjusted:** Dynamic sizing based on market volatility

## 🛠️ **Troubleshooting & Support**

### Common Issues

#### **Import Errors**
```bash
# Ensure all dependencies are installed
pip install -r requirements.txt --upgrade

# Check Python version compatibility
python --version  # Should be 3.8+
```

#### **Memory Issues with ML Models**
```bash
# Reduce model complexity or data range
python src/strategies/transformer_signal_strategy.py --fromdate 2023-06-01
```

#### **Web Server Port Conflicts**
```bash
# Use alternative port if 5000 is occupied
python src/app_server.py --port 8080
```

### Performance Monitoring
- **CPU Usage:** Monitor during backtests with `htop` or Task Manager
- **Memory Usage:** ML strategies require 4GB+ RAM for optimal performance
- **Disk Space:** HTML reports and model artifacts require storage space

## 🚀 **Deployment & Production**

### **Environment Setup**
```bash
# Production environment setup
python -m venv production_env
source production_env/bin/activate  # Linux/macOS
# OR
production_env\Scripts\activate     # Windows

pip install -r requirements.txt
```

### **Web Application Deployment**
```bash
# Production server with Gunicorn (Linux/macOS)
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 src.app_server:app

# Windows deployment with Waitress
pip install waitress
waitress-serve --port=5000 src.app_server:app
```

## 📚 **Additional Resources & Documentation**

### **Research & Methodology**
- **Time Series Transformer Research:** [Applied ML Trading Transformer for EUR/USD](https://github.com/ilahuerta-IA/applied-ml-trading-transformer-eurusd.git)
- **Backtrader Documentation:** [Official Backtrader Docs](https://www.backtrader.com/docu/)
- **Technical Analysis:** [TA-Lib Integration Guide](https://github.com/mrjbq7/ta-lib)

### **Development Guidelines**
```python
# Example: Adding a Custom Strategy
# File: src/strategies/my_custom_strategy.py

from src.strategies.base_strategy import BaseStrategy
import backtrader.indicators as btind

class MyCustomStrategy(BaseStrategy):
    params = (
        ('rsi_period', 14),
        ('rsi_upper', 70),
        ('rsi_lower', 30),
    )
    
    @staticmethod
    def get_parameter_definitions():
        return {
            'rsi_period': {'type': 'int', 'default': 14, 'min': 5, 'max': 50},
            'rsi_upper': {'type': 'float', 'default': 70.0, 'min': 60, 'max': 90},
            'rsi_lower': {'type': 'float', 'default': 30.0, 'min': 10, 'max': 40},
        }
    
    def __init__(self):
        super().__init__()
        self.rsi = btind.RSI(period=self.params.rsi_period)
        self.signals = []  # For HTML report visualization
    
    def next(self):
        if self.rsi > self.params.rsi_upper and self.position:
            self.sell()
            self.signals.append(('SELL', self.data.datetime.date(0), self.data.close[0]))
        elif self.rsi < self.params.rsi_lower and not self.position:
            self.buy()
            self.signals.append(('BUY', self.data.datetime.date(0), self.data.close[0]))
```

### **API Reference**

#### **Strategy Base Class**
```python
class BaseStrategy(bt.Strategy):
    """Base class for all trading strategies"""
    
    @staticmethod
    def get_parameter_definitions():
        """Return parameter definitions for web UI"""
        pass
    
    def __init__(self):
        """Initialize strategy indicators and signals"""
        pass
    
    def next(self):
        """Execute trading logic for each bar"""
        pass
```

#### **Data Format Specifications**
```python
# CSV Data Requirements
REQUIRED_COLUMNS = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']
DATE_FORMAT = '%Y-%m-%d %H:%M:%S'  # ISO format preferred
TIMEZONE = 'UTC'  # Recommended for consistency
```

## 🎯 **Future Enhancements & Roadmap**

### **Planned Features**
- 🔄 **Strategy Optimization:** Automated parameter optimization with genetic algorithms
- 📊 **Portfolio Rebalancing:** Dynamic asset allocation strategies
- 🌐 **Real-Time Data:** Integration with live market data feeds
- 📱 **Mobile Interface:** Responsive web design for mobile devices
- 🤖 **Advanced ML Models:** Integration with latest transformer architectures

### **Community Contributions**
```bash
# Contributing to the project
git fork <repository-url>
git checkout -b feature/new-strategy
# Implement your changes
git commit -m "Add new momentum strategy"
git push origin feature/new-strategy
# Create pull request
```

## 📋 **License & Acknowledgments**

### **License**
This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

### **Acknowledgments**
- **Backtrader:** Core backtesting engine by Daniel Rodriguez
- **Lightweight Charts™:** Professional financial charts by TradingView
- **Hugging Face Transformers:** State-of-the-art ML models
- **TensorFlow/Keras:** Neural network implementation framework

### **Disclaimer**
⚠️ **Important:** This software is for educational and research purposes only. Trading financial instruments involves substantial risk of loss and is not suitable for all investors. Past performance does not guarantee future results. Always consult with a qualified financial advisor before making trading decisions.

---


**Made with ❤️ for the quantitative trading community**

Distributed under the MIT License.

## Acknowledgements

*   [Backtrader](https://www.backtrader.com/)
*   [Flask](https://flask.palletsprojects.com/)
*   [Lightweight Charts™ by TradingView](https://www.tradingview.com/lightweight-charts/)
