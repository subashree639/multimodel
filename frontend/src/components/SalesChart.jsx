import { Line } from 'react-chartjs-2';
import { Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend } from 'chart.js';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend);

const SalesChart = ({ salesData }) => {
  const data = {
    labels: salesData?.labels || ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
    datasets: [
      {
        label: 'Revenue',
        data: salesData?.revenue || [12000, 19000, 15000, 18000, 22000, 25000],
        borderColor: '#1976d2',
        backgroundColor: 'rgba(25, 118, 210, 0.5)',
        tension: 0.4,
      },
      {
        label: 'Orders',
        data: salesData?.orders || [120, 190, 150, 180, 220, 250],
        borderColor: '#dc004e',
        backgroundColor: 'rgba(220, 0, 78, 0.5)',
        tension: 0.4,
      },
    ],
  };

  const options = {
    responsive: true,
    plugins: {
      legend: { position: 'top' },
      title: { display: true, text: 'Sales Analytics' },
    },
    scales: {
      y: {
        beginAtZero: true,
      },
    },
  };

  return <Line data={data} options={options} />;
};

export default SalesChart;