import { Bar } from 'react-chartjs-2';
import { Chart as ChartJS, CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend } from 'chart.js';

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend);

const ReviewChart = ({ sentimentData }) => {
  const data = {
    labels: ['Positive', 'Neutral', 'Negative'],
    datasets: [
      {
        label: 'Sentiment Score',
        data: [
          sentimentData?.positive || 33,
          sentimentData?.neutral || 34,
          sentimentData?.negative || 33,
        ],
        backgroundColor: ['#4caf50', '#ffc107', '#f44336'],
      },
    ],
  };

  const options = {
    responsive: true,
    plugins: {
      legend: { display: false },
      title: { display: true, text: 'Review Sentiment Analysis' },
    },
  };

  return <Bar data={data} options={options} />;
};

export default ReviewChart;